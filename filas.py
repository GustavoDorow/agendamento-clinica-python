from __future__ import annotations

from threading import RLock, Semaphore


class NoPaciente:
    def __init__(self, paciente: dict) -> None:
        self.paciente = paciente
        self.proximo: NoPaciente | None = None


class FilaPacientes:
    def __init__(self) -> None:
        self.head: NoPaciente | None = None
        self.tail: NoPaciente | None = None
        self.lock_mutex = RLock()
        self.quantidade = Semaphore(0)

    def esta_vazia(self) -> bool:
        with self.lock_mutex:
            return self.head is None

    def inserir_paciente(self, paciente: dict, ordenar: bool = False) -> None:
        no = NoPaciente(paciente)

        with self.lock_mutex:
            head = self.head
            tail = self.tail
            if head is None or tail is None:
                self.head = no
                self.tail = no
            elif not ordenar:
                tail.proximo = no
                self.tail = no
            elif paciente["horario"] < head.paciente["horario"]:
                no.proximo = head
                self.head = no
            else:
                anterior = head
                proximo = anterior.proximo
                # Horários iguais preservam a ordem de chegada.
                while (
                    proximo is not None
                    and proximo.paciente["horario"] <= paciente["horario"]
                ):
                    anterior = proximo
                    proximo = anterior.proximo
                no.proximo = proximo
                anterior.proximo = no
                if no.proximo is None:
                    self.tail = no

            self.quantidade.release()

    def retirar_paciente(self) -> dict | None:
        with self.lock_mutex:
            no = self.head
            if no is None or not self.quantidade.acquire(blocking=False):
                return None

            self.head = no.proximo
            if self.head is None:
                self.tail = None
            return no.paciente

    def listar_pacientes(self) -> list[dict]:
        with self.lock_mutex:
            pacientes: list[dict] = []
            no = self.head
            while no is not None:
                pacientes.append(no.paciente.copy())
                no = no.proximo
            return pacientes
