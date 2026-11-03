from __future__ import annotations

import math
import tkinter as tk
from tkinter import messagebox, ttk

from terminal import (
    aguardar_threads,
    criar_terminal,
    encerrar_terminal,
    enviar_chegada,
    formatar_horario,
    iniciar_terminal,
    obter_painel,
)


def iniciar_dia(tela: dict) -> None:
    try:
        intervalo = float(tela["intervalo"].get().replace(",", "."))
        proporcao = int(tela["proporcao"].get())
        if not math.isfinite(intervalo) or intervalo <= 0 or proporcao < 1:
            raise ValueError
    except ValueError:
        _ = messagebox.showerror(
            "Configuração inválida",
            "Use um intervalo positivo e N inteiro maior que zero.",
        )
        return

    estado = criar_terminal(intervalo, proporcao)
    tela["estado"] = estado
    tela["eventos_exibidos"] = 0
    _ = tela["eventos"].configure(state="normal")
    tela["eventos"].delete("1.0", "end")
    _ = tela["eventos"].configure(state="disabled")
    try:
        iniciar_terminal(estado)
    except RuntimeError as erro:
        _ = messagebox.showerror("Falha ao iniciar", str(erro))
        return
    _ = tela["iniciar"].configure(state="disabled")
    _ = tela["intervalo"].configure(state="disabled")
    _ = tela["proporcao"].configure(state="disabled")

    agenda = "; ".join(
        f"{consulta['nome']}: M{consulta['medico']} às {formatar_horario(consulta['horario'])}"
        for consulta in estado["agenda"]
    )
    _ = tela["agenda"].configure(text=f"Agenda simulada de {estado['dia']}:\n{agenda}")


def cadastrar_chegada(tela: dict) -> None:
    estado = tela["estado"]
    if estado is None:
        return
    erro = enviar_chegada(
        estado, tela["nome"].get(), tela["agendado"].get(), tela["prioritario"].get()
    )
    if erro:
        _ = messagebox.showinfo("Chegada", erro)
        return
    tela["nome"].delete(0, "end")
    tela["nome"].focus_set()


def atualizar_tipo_chegada(tela: dict) -> None:
    _ = tela["opcao_prioridade"].configure(
        state="disabled" if tela["agendado"].get() else "normal"
    )


def atualizar_painel(tela: dict) -> None:
    estado = tela["estado"]
    finalizado = True
    if estado is not None:
        painel = obter_painel(estado)
        finalizado = painel["finalizado"]
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
        _ = tela["horario"].configure(text=f"{formatar_horario(contador)} — {situacao}")
        vagas = painel["vagas"]
        _ = tela["vagas"].configure(
            text=f"Vagas do plantonista: manhã {vagas['manha']}/4 | tarde {vagas['tarde']}/4"
        )

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
        _ = tela["plantonista"].configure(
            text=f"Plantonista em consulta: {consulta['nome'] if consulta else '—'}"
        )

        novos_eventos = painel["eventos"][tela["eventos_exibidos"] :]
        if novos_eventos:
            _ = tela["eventos"].configure(state="normal")
            tela["eventos"].insert("end", "\n".join(novos_eventos) + "\n")
            tela["eventos"].see("end")
            _ = tela["eventos"].configure(state="disabled")
            tela["eventos_exibidos"] = len(painel["eventos"])

        aceita_chegadas = painel["situacao"] == "recepcao_aberta"
        _ = tela["chegada"].configure(state="normal" if aceita_chegadas else "disabled")
        if painel["finalizado"] and not tela["fechando"]:
            _ = tela["iniciar"].configure(text="Novo dia", state="normal")
            _ = tela["intervalo"].configure(state="normal")
            _ = tela["proporcao"].configure(state="normal")

    if tela["fechando"] and finalizado:
        tela["janela"].destroy()
        return
    _ = tela["janela"].after(100, lambda: atualizar_painel(tela))


def fechar_interface(tela: dict) -> None:
    tela["fechando"] = True
    _ = tela["iniciar"].configure(state="disabled")
    estado = tela["estado"]
    if estado is not None:
        encerrar_terminal(estado)


def executar_interface() -> None:
    janela = tk.Tk()
    janela.title("Terminal da Clínica")
    janela.geometry("1000x740")
    janela.minsize(800, 650)
    _ = janela.columnconfigure(0, weight=1)
    _ = janela.rowconfigure(0, weight=1)

    corpo = ttk.Frame(janela, padding=12)
    corpo.grid(sticky="nsew")
    _ = corpo.columnconfigure(0, weight=1)
    _ = corpo.rowconfigure(7, weight=1)

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

    horario = ttk.Label(
        corpo, text="08:00 — Configure e inicie o dia", font=("TkDefaultFont", 15)
    )
    horario.grid(row=1, column=0, sticky="w", pady=5)
    vagas = ttk.Label(corpo, text="Vagas do plantonista: manhã 4/4 | tarde 4/4")
    vagas.grid(row=2, column=0, sticky="w")

    chegada = ttk.LabelFrame(corpo, text="Chegada de paciente", padding=10)
    chegada.grid(row=3, column=0, sticky="ew", pady=10)
    _ = chegada.columnconfigure(1, weight=1)
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

    filas = ttk.Treeview(
        corpo, columns=("fila", "espera", "consulta"), show="headings", height=7
    )
    for coluna, titulo, largura in [
        ("fila", "Fila", 110),
        ("espera", "Pacientes em espera", 540),
        ("consulta", "Em consulta", 170),
    ]:
        filas.heading(coluna, text=titulo)
        _ = filas.column(coluna, width=largura)
    for indice, nome in enumerate(
        [f"Médico {numero}" for numero in range(1, 6)] + ["Prioritária", "Comum"]
    ):
        _ = filas.insert("", "end", iid=str(indice), values=(nome, "Vazia", "—"))
    filas.grid(row=4, column=0, sticky="ew")
    plantonista = ttk.Label(corpo, text="Plantonista em consulta: —")
    plantonista.grid(row=5, column=0, sticky="w", pady=5)

    ttk.Label(corpo, text="Registro de eventos").grid(row=6, column=0, sticky="w")
    registro = ttk.Frame(corpo)
    registro.grid(row=7, column=0, sticky="nsew")
    _ = registro.columnconfigure(0, weight=1)
    _ = registro.rowconfigure(0, weight=1)
    eventos = tk.Text(registro, height=10, wrap="word", state="disabled")
    eventos.grid(row=0, column=0, sticky="nsew")

    def rolar_eventos(acao: str, valor: str, unidade: str = "units") -> None:
        if acao == "moveto":
            eventos.yview_moveto(float(valor))
        elif acao == "scroll":
            eventos.yview_scroll(int(valor), "pages" if unidade == "pages" else "units")

    rolagem = ttk.Scrollbar(registro, command=rolar_eventos)
    rolagem.grid(row=0, column=1, sticky="ns")
    _ = eventos.configure(yscrollcommand=rolagem.set)

    rotulo_agenda = ttk.Label(
        corpo, text="A agenda simulada aparecerá ao iniciar o dia.", wraplength=950
    )
    rotulo_agenda.grid(row=8, column=0, sticky="ew", pady=(10, 0))
    tela: dict = {
        "janela": janela,
        "estado": None,
        "eventos_exibidos": 0,
        "fechando": False,
        "intervalo": intervalo,
        "proporcao": proporcao,
        "iniciar": iniciar,
        "horario": horario,
        "vagas": vagas,
        "nome": campo_nome,
        "agendado": agendado,
        "prioritario": prioritario,
        "opcao_prioridade": opcao_prioridade,
        "chegada": botao_chegada,
        "filas": filas,
        "plantonista": plantonista,
        "eventos": eventos,
        "agenda": rotulo_agenda,
    }

    def ajustar_agenda(evento: tk.Event[tk.Misc]) -> None:
        _ = rotulo_agenda.configure(wraplength=max(300, evento.width - 10))

    _ = corpo.bind("<Configure>", ajustar_agenda)
    janela.protocol("WM_DELETE_WINDOW", lambda: fechar_interface(tela))
    _ = janela.after(100, lambda: atualizar_painel(tela))
    try:
        janela.mainloop()
    finally:
        estado = tela["estado"]
        if estado is not None:
            encerrar_terminal(estado)
            aguardar_threads(estado)
