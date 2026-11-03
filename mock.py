from __future__ import annotations

from collections.abc import Callable
from threading import Condition, Event
from time import sleep


def criar_agenda(dia: str) -> list[dict]:
    return [
        {"nome": "Ana", "dia": dia, "medico": 1, "horario": 2},
        {"nome": "Bruno", "dia": dia, "medico": 1, "horario": 1},
        {"nome": "Carla", "dia": dia, "medico": 2, "horario": 3},
        {"nome": "Diego", "dia": dia, "medico": 2, "horario": 6},
        {"nome": "Elisa", "dia": dia, "medico": 3, "horario": 0},
        {"nome": "Fabio", "dia": dia, "medico": 3, "horario": 7},
        {"nome": "Gabriela", "dia": dia, "medico": 4, "horario": 8},
        {"nome": "Hugo", "dia": dia, "medico": 4, "horario": 3},
        {"nome": "Iara", "dia": dia, "medico": 5, "horario": 9},
        {"nome": "Joao", "dia": dia, "medico": 5, "horario": 6},
    ]


def consultar_agendamento(agenda: list[dict], nome: str, dia: str) -> dict | None:
    for consulta in agenda:
        if consulta["nome"].casefold() == nome.casefold() and consulta["dia"] == dia:
            return consulta.copy()
    return None


def simular_medico(
    medico: dict,
    condicao: Condition,
    parada: Event,
    segundos_por_hora: float,
    registrar_evento: Callable[[str], None],
) -> None:
    duracao = segundos_por_hora
    if medico["id"] != 0:
        duracao *= 0.6

    with condicao:
        medico["disponivel"] = True
        condicao.notify_all()

    while True:
        with condicao:
            # O paciente fica registrado mesmo se o aviso chegar antes do wait.
            while medico["atendimento"] is None and not parada.is_set():
                _ = condicao.wait()
            paciente = medico["atendimento"]
            if paciente is None:
                medico["disponivel"] = False
                return

        # Uma consulta iniciada termina mesmo depois do fechamento.
        sleep(duracao)

        with condicao:
            registrar_evento(
                f"{medico['nome']} concluiu o atendimento de {paciente['nome']}."
            )
            medico["atendimento"] = None
            medico["disponivel"] = not parada.is_set()
            condicao.notify_all()
