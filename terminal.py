from __future__ import annotations

from datetime import date
from threading import Condition, Event, RLock, Thread

from filas import FilaPacientes
from mock import consultar_agendamento, criar_agenda, simular_medico  # noqa: UP026 - módulo local do projeto


def criar_medico(numero: int) -> dict:
    return {
        "id": numero,
        "nome": f"Médico {numero}" if numero else "Plantonista",
        "fila": FilaPacientes(),
        "disponivel": False,
        "atendimento": None,
        "proximo": None,
    }


def criar_terminal(segundos_por_hora: float, proporcao: int) -> dict:
    if segundos_por_hora <= 0 or proporcao < 1:
        raise ValueError(
            "Configuração do terminal: intervalo e proporção devem ser positivos."
        )

    # Nas operações do Terminal, a ordem é mutex global e depois mutex da fila.
    lock_mutex = RLock()
    medicos: dict = {"head": None, "tail": None}
    for numero in range(1, 6):
        medico = criar_medico(numero)
        tail = medicos["tail"]
        if tail is None:
            medicos["head"] = medico
        else:
            tail["proximo"] = medico
        medicos["tail"] = medico

    dia = date.today().isoformat()
    return {
        "lock_mutex": lock_mutex,
        "condicao": Condition(lock_mutex),
        "parada": Event(),
        "ativo": True,
        "contador": 0,
        "dia": dia,
        "segundos_por_hora": segundos_por_hora,
        "proporcao": proporcao,
        "prioritarios_restantes": proporcao,
        "vagas": {"manha": 4, "tarde": 4},
        "medicos": medicos,
        "plantonista": criar_medico(0),
        "prioritaria": FilaPacientes(),
        "comum": FilaPacientes(),
        "chegadas": FilaPacientes(),
        "admitidos": set(),
        "agenda": criar_agenda(dia),
        "eventos": [],
        "threads": [],
    }


def formatar_horario(contador: int) -> str:
    return f"{8 + contador:02d}:00"


def registrar_evento(estado: dict, mensagem: str) -> None:
    with estado["lock_mutex"]:
        horario = formatar_horario(estado["contador"])
        estado["eventos"].append(f"[{horario}] {mensagem}")


def obter_turno(contador: int) -> str | None:
    if 0 <= contador <= 3:
        return "manha"
    if 6 <= contador <= 9:
        return "tarde"
    return None


def obter_situacao_clinica(estado: dict) -> str:
    with estado["lock_mutex"]:
        if not estado["ativo"] or estado["contador"] >= 10:
            return "expediente_encerrado"
        if estado["contador"] in (4, 5):
            return "almoco"
        if estado["contador"] >= 9:
            return "recepcao_fechada"
        return "recepcao_aberta"


def iniciar_terminal(estado: dict) -> None:
    def registrar_evento_mock(mensagem: str) -> None:
        registrar_evento(estado, mensagem)

    threads = [
        Thread(name="contador", target=contar_tempo, args=(estado,)),
        Thread(name="chegada", target=atender_chegadas, args=(estado,)),
        Thread(name="agendados", target=controlar_agendados, args=(estado,)),
        Thread(name="nao_agendados", target=controlar_nao_agendados, args=(estado,)),
    ]
    medico = estado["medicos"]["head"]
    while medico is not None:
        threads.append(
            Thread(
                name=f"medico_{medico['id']}",
                target=simular_medico,
                args=(
                    medico,
                    estado["condicao"],
                    estado["parada"],
                    estado["segundos_por_hora"],
                    registrar_evento_mock,
                ),
            )
        )
        medico = medico["proximo"]
    threads.append(
        Thread(
            name="plantonista",
            target=simular_medico,
            args=(
                estado["plantonista"],
                estado["condicao"],
                estado["parada"],
                estado["segundos_por_hora"],
                registrar_evento_mock,
            ),
        )
    )

    registrar_evento(estado, "Dia iniciado. Clínica aberta.")
    try:
        for thread in threads:
            thread.start()
            estado["threads"].append(thread)
    except RuntimeError:
        encerrar_terminal(estado)
        aguardar_threads(estado)
        raise


def encerrar_terminal(estado: dict) -> None:
    with estado["condicao"]:
        if not estado["ativo"]:
            return
        estado["ativo"] = False
        estado["parada"].set()
        registrar_evento(
            estado, "Expediente encerrado. Aguardando consultas em andamento."
        )

        while not estado["chegadas"].esta_vazia():
            paciente = estado["chegadas"].retirar_paciente()
            if paciente is not None:
                registrar_evento(
                    estado,
                    f"{paciente['nome']}: chegada pendente recusada no encerramento.",
                )

        filas = [estado["prioritaria"], estado["comum"]]
        medico = estado["medicos"]["head"]
        while medico is not None:
            filas.append(medico["fila"])
            medico = medico["proximo"]
        for fila in filas:
            for paciente in fila.listar_pacientes():
                registrar_evento(
                    estado, f"{paciente['nome']}: não atendido até o encerramento."
                )
        estado["condicao"].notify_all()


def aguardar_threads(estado: dict) -> None:
    for thread in estado["threads"]:
        thread.join()


def contar_tempo(estado: dict) -> None:
    while not estado["parada"].wait(estado["segundos_por_hora"]):
        with estado["condicao"]:
            if not estado["ativo"]:
                return
            estado["contador"] += 1
            contador = estado["contador"]
            if contador == 4:
                registrar_evento(estado, "Almoço. Novas consultas retomam às 14h.")
            elif contador == 6:
                registrar_evento(estado, "Início do turno da tarde.")
            elif contador == 9:
                registrar_evento(estado, "Recepção fechada para novas chegadas.")
            elif contador == 10:
                encerrar_terminal(estado)
            estado["condicao"].notify_all()


def enviar_chegada(
    estado: dict, nome: str, agendado: bool, prioritario: bool
) -> str | None:
    nome = nome.strip()
    if not nome:
        return "Informe o nome do paciente."
    with estado["condicao"]:
        situacao = obter_situacao_clinica(estado)
        if situacao == "expediente_encerrado":
            return "O expediente está encerrado."
        if situacao == "almoco":
            return "A clínica está fechada para almoço."
        if situacao == "recepcao_fechada":
            return "A recepção não aceita novas chegadas a partir das 17h."
        estado["chegadas"].inserir_paciente(
            {
                "nome": nome,
                "agendado": agendado,
                "prioritario": prioritario,
                "horario": 0,
            },
        )
        estado["condicao"].notify_all()
    return None


def atender_chegadas(estado: dict) -> None:
    with estado["condicao"]:
        while estado["ativo"]:
            while estado["chegadas"].esta_vazia() and estado["ativo"]:
                _ = estado["condicao"].wait()
            if not estado["ativo"]:
                return
            paciente = estado["chegadas"].retirar_paciente()
            if paciente is not None:
                admitir_paciente(estado, paciente)
            estado["condicao"].notify_all()


def admitir_paciente(estado: dict, paciente: dict) -> None:
    nome = paciente["nome"]
    contador = estado["contador"]
    turno = obter_turno(contador)
    if obter_situacao_clinica(estado) != "recepcao_aberta" or turno is None:
        registrar_evento(estado, f"{nome}: chegada recusada, recepção fechada.")
        return
    if nome.casefold() in estado["admitidos"]:
        registrar_evento(estado, f"{nome}: paciente já admitido neste dia.")
        return

    if paciente["agendado"]:
        consulta = consultar_agendamento(estado["agenda"], nome, estado["dia"])
        if consulta is None:
            registrar_evento(estado, f"{nome}: sem agendamento para hoje.")
            return
        if consulta["horario"] < contador:
            registrar_evento(estado, f"{nome}: chegada atrasada, consulta recusada.")
            return
        paciente["horario"] = consulta["horario"]
        medico = estado["medicos"]["head"]
        while medico is not None and medico["id"] != consulta["medico"]:
            medico = medico["proximo"]
        if medico is None:
            registrar_evento(estado, f"{nome}: médico do agendamento não encontrado.")
            return
        medico["fila"].inserir_paciente(paciente, ordenar=True)
        destino = (
            f"{medico['nome']}, consulta às {formatar_horario(paciente['horario'])}"
        )
    else:
        if estado["vagas"][turno] == 0:
            registrar_evento(estado, f"{nome}: sem vagas do plantonista neste turno.")
            return
        fila = estado["prioritaria"] if paciente["prioritario"] else estado["comum"]
        fila.inserir_paciente(paciente)
        estado["vagas"][turno] -= 1
        destino = "fila prioritária" if paciente["prioritario"] else "fila comum"

    estado["admitidos"].add(nome.casefold())
    registrar_evento(estado, f"{nome}: entrada aceita ({destino}).")


def iniciar_atendimento(estado: dict, medico: dict, paciente: dict) -> None:
    medico["disponivel"] = False
    medico["atendimento"] = paciente
    registrar_evento(
        estado, f"{medico['nome']} iniciou atendimento de {paciente['nome']}."
    )
    estado["condicao"].notify_all()


def controlar_agendados(estado: dict) -> None:
    with estado["condicao"]:
        while estado["ativo"]:
            if obter_situacao_clinica(estado) in (
                "recepcao_aberta",
                "recepcao_fechada",
            ):
                medico = estado["medicos"]["head"]
                while medico is not None:
                    if medico["disponivel"] and not medico["fila"].esta_vazia():
                        paciente = medico["fila"].retirar_paciente()
                        if paciente is not None:
                            iniciar_atendimento(estado, medico, paciente)
                    medico = medico["proximo"]
            # Hora, chegada ou disponibilidade podem tornar outra chamada possível.
            _ = estado["condicao"].wait()


def selecionar_nao_agendado(estado: dict) -> dict | None:
    prioritaria = estado["prioritaria"]
    comum = estado["comum"]
    if prioritaria.esta_vazia():
        estado["prioritarios_restantes"] = estado["proporcao"]
        return comum.retirar_paciente()

    if estado["prioritarios_restantes"] == 0:
        estado["prioritarios_restantes"] = estado["proporcao"]
        if not comum.esta_vazia():
            return comum.retirar_paciente()

    # Sem comuns, começa outro bloco de N prioritários, sem pausa artificial.
    estado["prioritarios_restantes"] -= 1
    return prioritaria.retirar_paciente()


def controlar_nao_agendados(estado: dict) -> None:
    medico = estado["plantonista"]
    with estado["condicao"]:
        while estado["ativo"]:
            if medico["disponivel"] and obter_situacao_clinica(estado) in (
                "recepcao_aberta",
                "recepcao_fechada",
            ):
                paciente = selecionar_nao_agendado(estado)
                if paciente is not None:
                    iniciar_atendimento(estado, medico, paciente)
            _ = estado["condicao"].wait()


def obter_painel(estado: dict) -> dict:
    with estado["lock_mutex"]:
        medicos: list[dict] = []
        medico = estado["medicos"]["head"]
        while medico is not None:
            medicos.append(
                {
                    "nome": medico["nome"],
                    "fila": medico["fila"].listar_pacientes(),
                    "atendimento": medico["atendimento"],
                }
            )
            medico = medico["proximo"]
        return {
            "ativo": estado["ativo"],
            "situacao": obter_situacao_clinica(estado),
            "contador": estado["contador"],
            "medicos": medicos,
            "prioritaria": estado["prioritaria"].listar_pacientes(),
            "comum": estado["comum"].listar_pacientes(),
            "plantonista": estado["plantonista"]["atendimento"],
            "vagas": estado["vagas"].copy(),
            "eventos": estado["eventos"].copy(),
            "finalizado": all(not thread.is_alive() for thread in estado["threads"]),
        }
