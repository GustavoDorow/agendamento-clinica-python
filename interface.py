from __future__ import annotations

import math
import tkinter as tk
from tkinter import messagebox, ttk
from tkinter.scrolledtext import ScrolledText

from terminal import (
    aguardar_threads,
    criar_terminal,
    encerrar_terminal,
    enviar_chegada,
    formatar_horario,
    iniciar_terminal,
    obter_painel,
)


def configurar_controles_dia(tela: dict, situacao: str) -> None:
    """Bloqueia ou libera a configuração e o início de um dia."""
    for nome in ("iniciar", "intervalo", "proporcao"):
        tela[nome].configure(state=situacao)


def iniciar_dia(tela: dict) -> None:
    try:
        intervalo = float(tela["intervalo"].get().replace(",", "."))
        proporcao = int(tela["proporcao"].get())
        if not math.isfinite(intervalo) or intervalo <= 0 or proporcao < 1:
            raise ValueError
    except ValueError:
        messagebox.showerror(
            "Configuração inválida",
            "Use um intervalo positivo e N inteiro maior que zero.",
        )
        return

    estado = criar_terminal(intervalo, proporcao)
    tela["estado"] = estado
    tela["eventos_exibidos"] = 0
    tela["eventos"].configure(state="normal")
    tela["eventos"].delete("1.0", "end")
    tela["eventos"].configure(state="disabled")
    try:
        iniciar_terminal(estado)
    except RuntimeError as erro:
        messagebox.showerror("Falha ao iniciar", str(erro))
        return
    configurar_controles_dia(tela, "disabled")

    agenda = "; ".join(
        f"{consulta['nome']}: M{consulta['medico']} às {formatar_horario(consulta['horario'])}"
        for consulta in estado["agenda"]
    )
    tela["agenda"].configure(text=f"Agenda simulada de {estado['dia']}:\n{agenda}")


def cadastrar_chegada(tela: dict) -> None:
    estado = tela["estado"]
    if estado is None:
        return
    erro = enviar_chegada(
        estado, tela["nome"].get(), tela["agendado"].get(), tela["prioritario"].get()
    )
    if erro:
        messagebox.showinfo("Chegada", erro)
        return
    tela["nome"].delete(0, "end")
    tela["nome"].focus_set()


def atualizar_tipo_chegada(tela: dict) -> None:
    tela["opcao_prioridade"].configure(
        state="disabled" if tela["agendado"].get() else "normal"
    )


def atualizar_filas(tela: dict, painel: dict) -> None:
    """Exibe as filas de espera e os atendimentos do painel recebido."""
    for indice, medico in enumerate(painel["medicos"]):
        espera = ", ".join(
            f"{paciente['nome']} ({formatar_horario(paciente['horario'])})"
            for paciente in medico["fila"]
        )
        consulta = medico["atendimento"]
        tela["filas"].item(
            str(indice),
            values=(
                medico["nome"],
                espera or "Vazia",
                consulta["nome"] if consulta else "—",
            ),
        )

    for indice, pacientes, nome in [
        (5, painel["prioritaria"], "Prioritária"),
        (6, painel["comum"], "Comum"),
    ]:
        espera = ", ".join(paciente["nome"] for paciente in pacientes)
        tela["filas"].item(str(indice), values=(nome, espera or "Vazia", "—"))
    consulta = painel["plantonista"]
    tela["plantonista"].configure(
        text=f"Plantonista em consulta: {consulta['nome'] if consulta else '—'}"
    )


def atualizar_eventos(tela: dict, eventos: list[str]) -> None:
    """Acrescenta ao registro somente os eventos ainda não exibidos."""
    novos_eventos = eventos[tela["eventos_exibidos"] :]
    if novos_eventos:
        tela["eventos"].configure(state="normal")
        tela["eventos"].insert("end", "\n".join(novos_eventos) + "\n")
        tela["eventos"].see("end")
        tela["eventos"].configure(state="disabled")
        tela["eventos_exibidos"] = len(eventos)


def atualizar_indicadores(tela: dict, painel: dict) -> None:
    """Exibe o horário, a situação da clínica e as vagas disponíveis."""
    contador = painel["contador"]
    if painel["situacao"] == "expediente_encerrado":
        situacao = (
            "Dia encerrado" if painel["finalizado"] else "Concluindo consultas"
        )
    elif painel["situacao"] == "almoco":
        situacao = "Almoço"
    elif painel["situacao"] == "recepcao_fechada":
        situacao = "Recepção fechada; atendimentos continuam"
    else:
        situacao = "Recepção aberta"
    tela["horario"].configure(text=f"{formatar_horario(contador)} — {situacao}")
    vagas = painel["vagas"]
    tela["vagas"].configure(
        text=f"Vagas do plantonista: manhã {vagas['manha']}/4 | tarde {vagas['tarde']}/4"
    )


def atualizar_painel(tela: dict) -> None:
    estado = tela["estado"]
    finalizado = True
    if estado is not None:
        painel = obter_painel(estado)
        finalizado = painel["finalizado"]
        atualizar_indicadores(tela, painel)
        atualizar_filas(tela, painel)
        atualizar_eventos(tela, painel["eventos"])

        aceita_chegadas = painel["situacao"] == "recepcao_aberta"
        tela["chegada"].configure(state="normal" if aceita_chegadas else "disabled")
        if painel["finalizado"] and not tela["fechando"]:
            tela["iniciar"].configure(text="Novo dia")
            configurar_controles_dia(tela, "normal")

    if tela["fechando"] and finalizado:
        tela["janela"].destroy()
        return
    tela["janela"].after(100, atualizar_painel, tela)


def fechar_interface(tela: dict) -> None:
    tela["fechando"] = True
    tela["iniciar"].configure(state="disabled")
    estado = tela["estado"]
    if estado is not None:
        encerrar_terminal(estado)


def montar_configuracao(corpo: ttk.Frame, tela: dict) -> None:
    """Monta os parâmetros de tempo e proporção do dia."""
    configuracao = ttk.Frame(corpo)
    configuracao.grid(row=0, column=0, sticky="ew", pady=(0, 10))
    ttk.Label(configuracao, text="Segundos por hora:").pack(side="left")
    intervalo = ttk.Entry(configuracao, width=8)
    intervalo.insert(0, "5")
    intervalo.pack(side="left", padx=(5, 15))
    ttk.Label(configuracao, text="Proporção N:1:").pack(side="left")
    proporcao = ttk.Entry(configuracao, width=5)
    proporcao.insert(0, "3")
    proporcao.pack(side="left", padx=5)
    iniciar = ttk.Button(
        configuracao, text="Iniciar dia", command=lambda: iniciar_dia(tela)
    )
    iniciar.pack(side="left", padx=10)
    tela["intervalo"] = intervalo
    tela["proporcao"] = proporcao
    tela["iniciar"] = iniciar


def montar_indicadores(corpo: ttk.Frame, tela: dict) -> None:
    """Monta os indicadores de horário e vagas do plantonista."""
    horario = ttk.Label(
        corpo, text="08:00 — Configure e inicie o dia", font=("TkDefaultFont", 15)
    )
    horario.grid(row=1, column=0, sticky="w", pady=5)
    vagas = ttk.Label(corpo, text="Vagas do plantonista: manhã 4/4 | tarde 4/4")
    vagas.grid(row=2, column=0, sticky="w")
    tela["horario"] = horario
    tela["vagas"] = vagas


def montar_chegada(corpo: ttk.Frame, tela: dict) -> None:
    """Monta o formulário de chegada de pacientes."""
    chegada = ttk.LabelFrame(corpo, text="Chegada de paciente", padding=10)
    chegada.grid(row=3, column=0, sticky="ew", pady=10)
    chegada.columnconfigure(1, weight=1)
    ttk.Label(chegada, text="Nome:").grid(row=0, column=0)
    campo_nome = ttk.Entry(chegada)
    campo_nome.grid(row=0, column=1, sticky="ew", padx=8)
    agendado = tk.BooleanVar(value=True)
    prioritario = tk.BooleanVar(value=False)
    ttk.Checkbutton(
        chegada,
        text="Possui agendamento",
        variable=agendado,
        command=lambda: atualizar_tipo_chegada(tela),
    ).grid(row=0, column=2)
    opcao_prioridade = ttk.Checkbutton(
        chegada, text="Prioritário", variable=prioritario, state="disabled"
    )
    opcao_prioridade.grid(row=0, column=3, padx=8)
    botao_chegada = ttk.Button(
        chegada,
        text="Registrar chegada",
        state="disabled",
        command=lambda: cadastrar_chegada(tela),
    )
    botao_chegada.grid(row=0, column=4)
    tela["nome"] = campo_nome
    tela["agendado"] = agendado
    tela["prioritario"] = prioritario
    tela["opcao_prioridade"] = opcao_prioridade
    tela["chegada"] = botao_chegada


def montar_filas(corpo: ttk.Frame, tela: dict) -> None:
    """Monta a tabela de filas e o indicador do plantonista."""
    filas = ttk.Treeview(
        corpo, columns=("fila", "espera", "consulta"), show="headings", height=7
    )
    for coluna, titulo, largura in [
        ("fila", "Fila", 110),
        ("espera", "Pacientes em espera", 540),
        ("consulta", "Em consulta", 170),
    ]:
        filas.heading(coluna, text=titulo)
        filas.column(coluna, width=largura)
    for indice, nome in enumerate(
        [f"Médico {numero}" for numero in range(1, 6)] + ["Prioritária", "Comum"]
    ):
        filas.insert("", "end", iid=str(indice), values=(nome, "Vazia", "—"))
    filas.grid(row=4, column=0, sticky="ew")
    plantonista = ttk.Label(corpo, text="Plantonista em consulta: —")
    plantonista.grid(row=5, column=0, sticky="w", pady=5)
    tela["filas"] = filas
    tela["plantonista"] = plantonista


def montar_registro(corpo: ttk.Frame, tela: dict) -> None:
    """Monta o registro de eventos com barra de rolagem integrada."""
    ttk.Label(corpo, text="Registro de eventos").grid(row=6, column=0, sticky="w")
    eventos = ScrolledText(corpo, height=10, wrap="word", state="disabled")
    eventos.grid(row=7, column=0, sticky="nsew")
    tela["eventos"] = eventos


def executar_interface() -> None:
    janela = tk.Tk()
    janela.title("Terminal da Clínica")
    janela.geometry("1000x740")
    janela.minsize(800, 650)
    janela.columnconfigure(0, weight=1)
    janela.rowconfigure(0, weight=1)

    corpo = ttk.Frame(janela, padding=12)
    corpo.grid(sticky="nsew")
    corpo.columnconfigure(0, weight=1)
    corpo.rowconfigure(7, weight=1)

    tela: dict = {
        "janela": janela,
        "estado": None,
        "eventos_exibidos": 0,
        "fechando": False,
    }
    montar_configuracao(corpo, tela)
    montar_indicadores(corpo, tela)
    montar_chegada(corpo, tela)
    montar_filas(corpo, tela)
    montar_registro(corpo, tela)

    rotulo_agenda = ttk.Label(
        corpo, text="A agenda simulada aparecerá ao iniciar o dia.", wraplength=950
    )
    rotulo_agenda.grid(row=8, column=0, sticky="ew", pady=(10, 0))
    tela["agenda"] = rotulo_agenda

    def ajustar_agenda(evento: tk.Event[tk.Misc]) -> None:
        rotulo_agenda.configure(wraplength=max(300, evento.width - 10))

    corpo.bind("<Configure>", ajustar_agenda)
    janela.protocol("WM_DELETE_WINDOW", lambda: fechar_interface(tela))
    janela.after(100, atualizar_painel, tela)
    try:
        janela.mainloop()
    finally:
        estado = tela["estado"]
        if estado is not None:
            encerrar_terminal(estado)
            aguardar_threads(estado)
