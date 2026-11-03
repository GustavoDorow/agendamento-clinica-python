# Entrega 1 — Sistema de Agendamento e Atendimento em Clínica (INE5611)

A primeira entrega, prevista para 03/11/2026, consiste em implementar o Programa Terminal completo e funcional. Ele representa a recepção da clínica, controlando a chegada de pacientes, suas filas, o horário de funcionamento e a distribuição dos atendimentos.

O Servidor, as Secretárias e os Front Ends reais dos médicos não precisam estar implementados ainda. Eles serão substituídos por simulações (mocks) nesta etapa.&#x20;

trabalho INE5611_2026_2.pdf



Vou utilizar C com `pthreads` para exemplificar a arquitetura e mostrar como uma função `main()` deve inicializar e chamar toda a lógica.

## 1. O que o programa precisa fazer

Imagine a clínica funcionando às 08:00.

1. O Terminal inicia com o contador de tempo em `0`, representando 08:00.
2. Um paciente chega e informa se possui agendamento.
3. Se possui, o Terminal consulta o Servidor simulado para descobrir seu médico e horário.
4. Se não possui, o Terminal verifica se há vagas e o coloca na fila comum ou prioritária.
5. Quando um médico sinaliza que está disponível, a thread de controle seleciona um paciente elegível.
6. O médico atende esse paciente durante um intervalo de tempo simulado.
7. Ao terminar, o médico sinaliza que está disponível novamente.
8. Enquanto isso, o relógio avança, os pacientes continuam chegando e as filas são atualizadas.

Tudo isso acontece concorrentemente, com diferentes threads executando dentro do mesmo processo.

## 2. Arquitetura do Terminal

O enunciado exige quatro threads principais, além das threads temporárias que simulam os cinco médicos e o plantonista.

`main()` — Processo Terminal

Inicializa o sistema, cria as threads e executa a interface gráfica

Cria e coordena

Contador de Tempo

Atualiza o relógio lógico

Atendimento de Chegada

Recebe e classifica pacientes

Controle de Agendados

Gerencia as 5 filas dos médicos

Controle de Não Agendados

Aplica a política de prioridade

Recursos compartilhados e sincronizados

Contador de tempo

Filas dos 5 médicos

Fila prioritária

Fila comum

Threads de simulação

5 médicos simulados + 1 plantonista simulado + Servidor mock (funções locais)

O Servidor mock não precisa de uma thread própria: pode ser uma função chamada pela thread de chegada. Já os médicos simulados precisam executar de maneira independente para testar corretamente os sinais de disponibilidade.

### Estrutura sugerida de arquivos

```
clinica/
├── main.c
├── terminal.h
├── terminal.c
├── contador.c
├── chegada.c
├── agendados.c
├── nao_agendados.c
├── filas.h
├── filas.c
├── servidor_mock.c
├── simuladores.c
├── interface.c
├── Makefile
└── README.md
```

Essa organização é uma sugestão de implementação, não uma estrutura de diretórios obrigatória do enunciado.

## 3. Como implementar a função `main()`

A `main()` deve ser responsável por inicializar, iniciar e finalizar o sistema, deixando as regras de negócio em funções separadas.

Uma boa implementação seria:

```

#include <stdio.h>
#include "terminal.h"
#include "interface.h"

int main(void) {
    // 1. Cria o estado do terminal.
    // 5 = segundos por hora simulada.
    Terminal *terminal = terminal_criar(5);

    if (terminal == NULL) {
        fprintf(stderr, "Erro ao criar terminal.\n");
        return 1;
    }

    // 2. Inicializa o servidor simulado e as filas.
    terminal_inicializar(terminal);

    // 3. Cria as threads do sistema.
    if (terminal_iniciar(terminal) != 0) {
        fprintf(stderr, "Erro ao iniciar threads.\n");
        terminal_destruir(terminal);
        return 1;
    }

    // 4. Executa a interface gráfica.
    // Essa função bloqueia até a janela ser fechada.
    interface_executar(terminal);

    // 5. Solicita a parada das threads.
    terminal_solicitar_parada(terminal);

    // 6. Aguarda todas as threads terminarem.
    terminal_aguardar_threads(terminal);

    // 7. Libera memória, mutexes e semáforos.
    terminal_destruir(terminal);

    return 0;
}

```

Esse é um esqueleto de arquitetura, não um programa completo compilável isoladamente: as funções chamadas devem ser implementadas nos módulos correspondentes.

### O que acontece dentro de `terminal_iniciar()`?

Essa função cria as quatro threads obrigatórias e as seis threads de simulação.

```

int terminal_iniciar(Terminal *t) {

    // Threads principais do Terminal
    pthread_create(
        &t->thread_tempo, NULL,
        thread_contador, t
    );

    pthread_create(
        &t->thread_chegada, NULL,
        thread_atendimento_chegada, t
    );

    pthread_create(
        &t->thread_agendados, NULL,
        thread_controle_agendados, t
    );

    pthread_create(
        &t->thread_nao_agendados, NULL,
        thread_controle_nao_agendados, t
    );

    // Cinco médicos simulados
    for (int i = 0; i < 5; i++) {
        t->contextos_medicos[i].terminal = t;
        t->contextos_medicos[i].id = i;

        pthread_create(
            &t->threads_medicos[i], NULL,
            thread_medico_mock,
            &t->contextos_medicos[i]
        );
    }

    // Um plantonista simulado
    pthread_create(
        &t->thread_plantonista, NULL,
        thread_plantonista_mock, t
    );

    return 0;
}

```

Exemplo simplificado de inicialização, com atributos declarados na struct Terminal. Na implementação definitiva, verifique o retorno de cada pthread_create e trate falhas de inicialização.

Assim, o processo possui dez threads de trabalho: quatro do Terminal e seis simuladoras. A `main()` permanece na interface gráfica.

## 4. O que cada thread deve executar

### 4.1. Thread Contador de Tempo

Responsável pelo relógio da clínica.

O contador é um inteiro, compartilhado entre as threads do Terminal.

| Contador | Hora        | Situação                      |
| -------- | ----------- | ----------------------------- |
| 0–3      | 08:00–11:00 | Turno da manhã                |
| 4–5      | 12:00–13:00 | Almoço                        |
| 6–8      | 14:00–16:00 | Tarde, novas chegadas aceitas |
| 9        | 17:00       | Sem novas chegadas            |
| 10       | 18:00       | Encerramento                  |

Simulação do contador

Contador: 10

# 18:00

Fim do expediente

&#x20;AnteriorPróxima hora&#x20;

Interaja com os botões para observar as mudanças de horário e de funcionamento.

O funcionamento da função da thread seria:

```
void *thread_contador(void *arg) {
    Terminal *t = arg;

    while (terminal_esta_ativo(t)) {
        sleep(t->segundos_por_hora);

        // Modifica contador sob proteção do mutex.
        avancar_tempo(t);

        // Avisa threads que dependem da hora.
        notificar_mudanca_de_hora(t);

        if (obter_contador(t) >= 10) {
            iniciar_encerramento(t);
            break;
        }
    }

    return NULL;
}
```

A função `avancar_tempo()` deve usar um mutex para modificar o contador. A mudança de hora também deve acordar threads bloqueadas esperando pelo próximo turno, usando uma variável de condição.

### 4.2. Thread Atendimento de Chegada

Essa thread recebe os pacientes enviados pela interface gráfica.

Paciente chega ao Terminal

Verifica se a clínica aceita chegadas

Agendado

Consulta Servidor mock

Verifica horário e médico

Entra na fila do médico correspondente

Não agendado

Verifica vagas do plantonista

Identifica prioridade

Entra na fila comum ou prioritária

Exemplo de paciente agendado:

A paciente Ana chega às 09:00 e informa que possui consulta.

O Terminal faz:

```
RespostaAgenda resposta =
    servidor_mock_consultar("Ana", dia_atual);
```

O mock retorna, por exemplo:

```
Médico: 2
Horário: 11:00 (contador 3)
```

Como o contador atual é 1 e o agendamento é para 3, Ana pode entrar na fila do médico 2.

Se o contador já fosse 4, a consulta estaria atrasada e Ana seria recusada.

Exemplo de paciente não agendado:

Bruno chega às 10:00, sem consulta marcada.

O Terminal verifica:

- Está dentro do turno da manhã?
- Ainda existe um dos quatro slots do plantonista?
- Bruno é prioritário ou comum?

Se houver slot disponível, Bruno entra na fila correspondente e um slot é consumido.

O controle de slots deve ser sincronizado para impedir que duas chegadas simultâneas ocupem a última vaga.

### 4.3. Thread de Controle da Fila de Agendados

O Terminal possui cinco filas independentes, uma para cada médico.

```
Médico 0: [Ana 09:00] -> [Carlos 11:00]
Médico 1: [Maria 10:00]
Médico 2: [Pedro 14:00] -> [João 16:00]
Médico 3: [vazia]
Médico 4: [Luiza 15:00]
```

Cada fila é ordenada pelo horário da consulta entre os pacientes que já chegaram.

Quando o médico 2 sinaliza que está disponível, a thread de controle:

1. Verifica se existe paciente na fila do médico 2.
2. Se houver, remove o primeiro paciente.
3. Envia o paciente para o médico 2.
4. Marca o médico como ocupado.

Se a fila estiver vazia, a disponibilidade do médico precisa ficar registrada. Quando um paciente chegar, o atendimento poderá começar sem exigir um novo sinal do médico.

Isso é importante para evitar lost wakeups, isto é, sinais de disponibilidade perdidos.&#x20;

trabalho INE5611_2026_2.pdf



### 4.4. Thread de Controle das Filas de Não Agendados

Essa thread gerencia duas filas:

```
Fila prioritária:
    [Ana] -> [Bruno] -> [Carlos] -> [Daniel]

Fila comum:
    [Eduardo] -> [Fernanda] -> [Gabriel]
```

O enunciado exige o algoritmo Múltiplas Filas com Alternância Proporcional.

Com `N = 3`, quando ambas as filas têm pacientes, a seleção segue:

Escalonamento 3:1

Atendimento 1 de 8

Prioritário

Prioritário

Prioritário

Comum

Prioritário

Prioritário

Prioritário

Comum

Paciente selecionado

Ana

Atendimento prioritário; a proporção permite até três prioritários antes do próximo comum.

ReiniciarPróximo paciente

A política precisa tratar também as exceções: se uma das filas estiver vazia, o plantonista não fica ocioso artificialmente. Quando novos pacientes surgirem, a contagem da proporção deverá ser respeitada ou reiniciada conforme as regras do enunciado.&#x20;

trabalho INE5611_2026_2.pdf



## 5. Como implementar a sincronização

Esta é a parte mais importante do trabalho: 55% da avaliação da primeira entrega corresponde à correção da sincronização e ao uso adequado das primitivas.&#x20;

trabalho INE5611_2026_2.pdf



Eu organizaria os recursos desta forma:

| Recurso                        | Primitivas sugeridas                |
| ------------------------------ | ----------------------------------- |
| Contador de tempo              | `pthread_mutex_t`, `pthread_cond_t` |
| Cada fila de médico            | `pthread_mutex_t`, `sem_t`          |
| Fila prioritária               | `pthread_mutex_t`, `sem_t`          |
| Fila comum                     | `pthread_mutex_t`, `sem_t`          |
| Sinais dos médicos             | Mutex e variáveis de condição       |
| Disponibilidade do plantonista | Mutex e variável de condição        |
| Fila de eventos de chegada     | Mutex e semáforo                    |

Um exemplo da estrutura de uma fila seria:

```
typedef struct {
    NoPaciente *inicio;
    NoPaciente *fim;

    pthread_mutex_t mutex;
    sem_t quantidade;
} FilaPacientes;
```

O mutex protege a manipulação da lista encadeada, e o semáforo contabiliza os pacientes disponíveis.

A operação de inserção seria, conceitualmente:

```
void fila_inserir(FilaPacientes *fila, Paciente p) {
    pthread_mutex_lock(&fila->mutex);

    inserir_no_final(fila, p);

    pthread_mutex_unlock(&fila->mutex);

    sem_post(&fila->quantidade);
}
```

Já a retirada precisa reservar um item no semáforo antes de remover o nó, garantindo que não tente retirar de uma fila vazia.

Para filas agendadas, a inserção deve ser ordenada pelo horário, em vez de simplesmente inserir no final.

Também recomendo estabelecer estas regras de implementação:

- Nunca executar `sleep()` segurando um mutex.
- Sempre verificar uma condição compartilhada em um `while` ao usar `pthread_cond_wait()`.
- Definir e documentar a ordem de aquisição de mutexes.
- Não acessar widgets da GUI diretamente a partir das threads de trabalho; no GTK, encaminhar atualizações à thread principal, por exemplo com `g_idle_add()`.

## 6. Como os médicos simulados funcionam

Na primeira entrega, o médico não é outro processo. Ele pode ser representado por uma thread de teste.

O ciclo deve funcionar assim:

```
void *thread_medico_mock(void *arg) {
    ContextoMedico *ctx = arg;
    Terminal *t = ctx->terminal;
    int id = ctx->id;

    while (terminal_esta_ativo(t)) {

        // Médico avisa que está disponível.
        medico_sinalizar_disponivel(t, id);

        // Aguarda paciente enviado pelo controlador.
        Paciente p;

        if (!medico_aguardar_paciente(t, id, &p)) {
            break;
        }

        // Registra início do atendimento.
        registrar_inicio_atendimento(t, id, p);

        // Simula a consulta.
        simular_duracao_consulta(t);

        // Registra conclusão.
        registrar_fim_atendimento(t, id, p);

        // Na próxima iteração, sinaliza novamente.
    }

    return NULL;
}
```

As funções auxiliares acima são responsabilidade do módulo de simulação e sincronização.

O plantonista segue um ciclo equivalente, mas recebe pacientes da thread que controla as filas comum e prioritária.

A consulta simulada deve durar menos que o intervalo real configurado para uma hora lógica. A duração máxima e a sinalização de conclusão fazem parte dos requisitos.&#x20;

trabalho INE5611_2026_2.pdf



## 7. Exemplo completo de funcionamento

Considere o contador configurado para avançar a cada cinco segundos reais.

| Hora  | Evento                             | Resultado                                                |
| ----- | ---------------------------------- | -------------------------------------------------------- |
| 08:00 | Sistema inicia                     | Filas vazias, médicos livres                             |
| 08:00 | Ana chega, agendada para 10:00     | Inserida na fila do médico 1                             |
| 08:00 | Bruno chega, prioritário           | Inserido na fila prioritária                             |
| 08:00 | Plantonista envia OK               | Bruno é selecionado                                      |
| 09:00 | Carlos chega, comum                | Inserido na fila comum                                   |
| 10:00 | Médico 1 fica livre                | Seleciona o primeiro da sua fila                         |
| 12:00 | Início do almoço                   | Nenhum novo atendimento iniciado durante o intervalo     |
| 14:00 | Retorno do almoço                  | Atendimentos podem ser retomados                         |
| 17:00 | Terminal fecha para novas chegadas | Pacientes já admitidos continuam elegíveis               |
| 18:00 | Encerramento                       | Finaliza atendimentos em andamento e encerra a simulação |

Esse é um cenário demonstrativo, não uma sequência fixa que o programa precisa produzir.

## 8. Interface gráfica esperada

A interface deve permitir cadastrar chegadas e acompanhar o estado interno sem bloquear as threads.

Um layout simples pode mostrar:

Terminal da Clínica

Exemplo visual da primeira entrega

Em operação

Horário

## 10:00

Esperando

## 7

Em consulta

## 3

Filas de espera

Médico 1

Ana, João

2

Médico 2

Maria

1

Médico 3

Sem pacientes

0

Médico 4

Carlos

1

Médico 5

Sem pacientes

0

Prioritários

Bruno, Felipe

2

Comuns

Eduardo

1

Registro de eventos

[09:00] Ana admitida na fila do Médico 1\
[09:00] Bruno admitido como prioritário\
[10:00] Médico 1 iniciou atendimento\
[10:00] Eduardo entrou na fila comum

Ilustração da interface; os dados são fictícios.

## 9. O que precisa ser entregue

Além do código-fonte funcionando, o enunciado exige o README, o relatório parcial de 2 a 4 páginas e a demonstração em laboratório.&#x20;

trabalho INE5611_2026_2.pdf



Checklist da Entrega 1

0/10

As quatro threads obrigatórias são criadas e executadas.

O contador avança e os turnos são respeitados.

Os pacientes agendados entram na fila correta e ordenada.

O Terminal recusa pacientes atrasados.

As filas comum e prioritária funcionam com a proporção configurada.

Os quatro slots por turno do plantonista são controlados.

Os cinco médicos e o plantonista simulados executam o ciclo de atendimento.

Mutexes, semáforos e variáveis de condição são usados corretamente.

A GUI mostra filas, horário, atendimentos e eventos.

O README e o relatório parcial documentam o sistema e os testes.

## 10. Ordem recomendada de implementação

Eu começaria implementando as estruturas de pacientes e filas, depois o relógio e seus mecanismos de sincronização. Em seguida, desenvolveria a chegada de pacientes e os dois controladores de atendimento. Só então integraria os médicos simulados e a interface gráfica.

A ideia central é que a `main()` apenas coordene a inicialização. A lógica deve ficar nos módulos e nas threads, que operam concorrentemente sobre um estado compartilhado devidamente protegido.

Isso facilita a segunda entrega: será possível substituir o Servidor mock pelo real e trocar as threads dos médicos simulados por comunicação com processos externos, preservando a maior parte da lógica do Terminal.
