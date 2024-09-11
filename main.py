import csv
from datetime import datetime
import sys
import mysql.connector
 from PyQt5.QtCore import QDate, QTimer
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtWidgets import QApplication, QHBoxLayout, QMainWindow, QMessageBox, QDialog, QFormLayout, QLineEdit, \
    QAbstractItemView
from PyQt5.QtWidgets import QDialogButtonBox, QTableWidget, QTableWidgetItem
from PyQt5.QtWidgets import QDateEdit, QTextEdit, QWidget, QVBoxLayout, QPushButton, QLabel, QGridLayout, QFileDialog
from PyQt5.QtWidgets import QComboBox, QTabWidget, QGroupBox
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


# Configuração do banco de dados
DB_CONFIG = {
    'user': 'root',
    'password':"" ,
    'host': 'localhost',
    'database': 'sistema_fluxo_caixa'
}


def inicializar_banco():
    connection = mysql.connector.connect(**DB_CONFIG)
    cursor = connection.cursor()

    # Criação das tabelas se não existirem
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INT AUTO_INCREMENT PRIMARY KEY,
            nome VARCHAR(255) NOT NULL UNIQUE,
            senha VARCHAR(255) NOT NULL,
            nivel ENUM('admin', 'gerente', 'cozinha', 'garcom') NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS estoque (
            id INT AUTO_INCREMENT PRIMARY KEY,
            nome VARCHAR(255) NOT NULL,
            tipo VARCHAR(255),
            setor VARCHAR(255),
            peso VARCHAR(255) NOT NULL,      
            quantidade INT NOT NULL
        )
    ''')
    try:
        cursor.execute('INSERT INTO usuarios (nome, senha, nivel) VALUES (%s, %s, %s)', ("Leo", "LeoE1324", "admin"))
        connection.commit()
    except mysql.connector.IntegrityError:
        pass  # Usuário já existe
    return connection, cursor


connection, cursor = inicializar_banco()


def adicionar_usuario_bd(nome_usuario, senha_usuario, nivel_usuario):
    try:
        cursor = connection.cursor()
        cursor.execute('INSERT INTO usuarios (nome, senha, nivel) VALUES (%s, %s, %s)',
                       (nome_usuario, senha_usuario, nivel_usuario))
        connection.commit()  # Confirmar a transação
        print("Usuário adicionado com sucesso!")
    except mysql.connector.Error as err:
        print(f"Erro ao adicionar usuário: {err}")
        connection.rollback()  # Reverter a transação em caso de erro
    finally:
        cursor.close()


def remover_usuario_bd(nome_usuario):
    try:
        cursor = connection.cursor()
        cursor.execute('DELETE FROM usuarios WHERE nome = %s', (nome_usuario,))
        connection.commit()
    except mysql.connector.Error as err:
        print(f"Erro ao remover usuário: {err}")
        connection.rollback()
    finally:
        cursor.close()


def listar_usuarios_bd():
    try:
        cursor = connection.cursor()
        cursor.execute('SELECT nome, nivel FROM usuarios')
        usuarios = cursor.fetchall()
        return usuarios
    except mysql.connector.Error as err:
        print(f"Erro ao listar usuários: {err}")
        return []
    finally:
        cursor.close()


class LoginDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Login")
        self.setGeometry(100, 100, 300, 150)
        self.setWindowIcon(QIcon("C:/Users/leand/workspace/Python_Works/Programador_Junior/Sistema_gerenciamento/logo_rest.png"))
        # Aplicando estilo CSS para o diálogo de login
        self.setStyleSheet("""
            QDialog {
                background-color: #3b0000; /* Cor de fundo do diálogo */
            }
            QLabel {
                color: #ffffff; /* Cor do texto dos rótulos */
            }
            QLineEdit {
                background-color: #aaaaaa; /* Cor de fundo dos campos de entrada */
                color: #000000; /* Cor do texto dos campos de entrada */
                border: 1px solid white; /* Borda dos campos de entrada */
                border-radius: 8px;
                padding: 5px; /* Espaçamento interno dos campos */
            }
            QPushButton {
                background-color: #590000; /* Cor de fundo dos botões */
            color: white;
            border: 2px solid #7e0000;
            border-radius: 8px;
            padding: 2px 20px;
            font-size: 14px;
            }
            QPushButton:hover {
                background-color: #7e0000; /* Cor de fundo dos botões ao passar o mouse */
            }
        """)

        layout = QFormLayout(self)
        self.nome_usuario = QLineEdit(self)
        self.senha_usuario = QLineEdit(self)
        self.senha_usuario.setEchoMode(QLineEdit.Password)

        layout.addRow("Nome de Usuário:", self.nome_usuario)
        layout.addRow("Senha:", self.senha_usuario)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.hide()

    def get_user_credentials(self):
        """Obtém as credenciais do usuário inseridas no diálogo."""
        return self.nome_usuario.text(), self.senha_usuario.text()


# Função de autenticação que puxa do banco de dados
def autenticar_usuario(nome_usuario, senha_usuario):
    try:
        cursor = connection.cursor()
        cursor.execute('SELECT senha FROM usuarios WHERE nome = %s', (nome_usuario,))
        resultado = cursor.fetchone()
        if resultado and resultado[0] == senha_usuario:
            return True
        return False
    except mysql.connector.Error as err:
        print(f"Erro ao autenticar usuário: {err}")
        return False
    finally:
        cursor.close()


# Função que obtém o tipo de usuário do banco de dados
def obter_tipo_usuario(nome_usuario):
    try:
        cursor = connection.cursor()
        cursor.execute('SELECT nivel FROM usuarios WHERE nome = %s', (nome_usuario,))
        resultado = cursor.fetchone()
        if resultado:
            return resultado[0]
        return "desconhecido"
    except mysql.connector.Error as err:
        print(f"Erro ao obter tipo de usuário: {err}")
        return "desconhecido"
    finally:
        cursor.close()


class SistemaVendas(QMainWindow):
    def __init__(self, tipo_usuario, nome_usuario, login_dialog):
        super().__init__()
        self.nome_restaurante = "Restaurante Cozinha da Dodô"
        self.forma_pagamento_combo = QComboBox()
        self.dividas_table = QTableWidget()
        self.dividas = []
        self.saldo_label = QLabel()
        self.tipo_usuario = tipo_usuario
        self.nome_usuario = nome_usuario
        self.login_dialog = login_dialog  # Armazena a instância de login_dialog
        self.setWindowTitle("Sistema de Vendas")
        self.setGeometry(100, 100, 800, 600)
        # Definindo o ícone da janela
        self.setWindowIcon(QIcon("C:/Users/leand/workspace/Python_Works/Programador_Junior/Sistema_gerenciamento/logo_rest.png"))  # Substitua pelo caminho do ícone da sua logo
        self.setStyleSheet("""
            QMainWindow {
                background-color: #7e0000; /* Cor de fundo do diálogo */
            }
            QLabel {
                color: black; /* Cor do texto dos rótulos */
            }
            QLineEdit {
                background-color: #aaaaaa; /* Cor de fundo dos campos de entrada */
                color: #000000; /* Cor do texto dos campos de entrada */
                border: 1px solid white; /* Borda dos campos de entrada */
                border-radius: 8px;
                padding: 2px 10px; /* Espaçamento interno dos campos */
            }
            QPushButton {
                background-color: #590000; /* Cor de fundo dos botões */
                color: White;
                border: 2px solid #7e0000;
                border-radius: 8px;
                padding: 2px 10px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #7e0000; /* Cor de fundo dos botões ao passar o mouse */
                border: 2px solid #590000;
                border-radius: 8px;
            }
        """)

        # Central Widget and Layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)



        # Adiciona o QLabel de apresentação
        self.apresentacao = QLabel(f"Olá {self.tipo_usuario.capitalize()} {self.nome_usuario}")
        self.apresentacao.setFont(QFont("Impact", 8))
        self.apresentacao.setStyleSheet("color: White;")
        layout.addWidget(self.apresentacao)
        # Adiciona o QLabel para data e hora
        self.data_hora_label = QLabel()
        self.data_hora_label.setFont(QFont("Impact", 8))
        self.data_hora_label.setStyleSheet("color: White;")
        layout.addWidget(self.data_hora_label)

        # Configura o QTimer para atualizar a data e hora
        self.timer = QTimer()
        self.timer.timeout.connect(self.atualizar_data_hora)
        self.timer.start(1000)  # Atualiza a cada segundo

        # Botão de Sair
        sair_button = QPushButton("Sair")
        sair_button.clicked.connect(self.voltar_para_login)
        layout.addWidget(sair_button)

        # Tab Widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        # Abas
        if self.tipo_usuario in ["admin", "gerente"]:
            self.tab_vendas = QWidget()
            self.tab_dividas = QWidget()
            self.tab_pagamentos = QWidget()
            self.tab_estoque = QWidget()
            self.tab_relatorios = QWidget()
            self.tab_usuarios = QWidget()

            self.tab_widget.addTab(self.tab_vendas, "Vendas")
            self.tab_widget.addTab(self.tab_dividas, "Débitos")
            self.tab_widget.addTab(self.tab_pagamentos, "Pagamentos")
            self.tab_widget.addTab(self.tab_estoque, "Estoque")
            self.tab_widget.addTab(self.tab_relatorios, "Relatórios")
            self.tab_widget.addTab(self.tab_usuarios, "Usuários")

            # Definições de configuração de abas
            self.setup_vendas_tab()
            self.setup_dividas_tab()
            self.setup_pagamentos_tab()
            self.setup_estoque_tab()
            self.setup_relatorios_tab()
            self.setup_usuarios_tab()
        else:
            self.tab_estoque = QWidget()
            self.tab_widget.addTab(self.tab_estoque, "Estoque")
            self.setup_estoque_tab()

        layout.addWidget(sair_button)

        self.transacoes = []
        self.saldo_atual = 0.0  # Inicializa o saldo



    def voltar_para_login(self):
        self.hide()  # Esconde a janela atual (principal)
        self.login_dialog.show()  # Mostra a janela de login novamente

    def atualizar_data_hora(self):
        data_hora_atual = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        self.data_hora_label.setText(f"Data e Hora Atual: {data_hora_atual}")

    def setup_vendas_tab(self):
        layout = QVBoxLayout(self.tab_vendas)

        # Saldo
        self.saldo_label.setText("Saldo Atual: R$ 0.00")
        self.saldo_label.setFont(QFont("Impact", 16))
        self.saldo_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.saldo_label)

        # Área de texto para mostrar transações
        self.transacoes_text_area = QTextEdit(self)
        self.transacoes_text_area.setPlaceholderText("As transações serão exibidas aqui...")
        self.transacoes_text_area.setReadOnly(True)
        layout.addWidget(self.transacoes_text_area)

        # Forma de Pagamento
        self.forma_pagamento_combo.addItems(
            ["Selecione", "Pagamento de Débito", "Dinheiro", "Cartão de Débito", "Cartão de Crédito( Á Vista )",
             "Cartão de Crédito( 30 Dias )", "Pix"])
        forma_pagamento_group = QGroupBox("Forma de Pagamento")
        forma_pagamento_layout = QHBoxLayout(forma_pagamento_group)
        forma_pagamento_layout.addWidget(self.forma_pagamento_combo)
        layout.addWidget(forma_pagamento_group)

        # Seções de Vendas
        self.setup_comidas(layout)
        self.setup_bebidas(layout)
        self.setup_outros(layout)

    def setup_comidas(self, layout):
        comida_group = QGroupBox("Comidas:")
        comida_layout = QGridLayout(comida_group)
        comidas = [
            ("Quentinha Grande", 18.00),
            ("Quentinha Pequena", 12.00),
            ("Vianda Pequena", 18.00),
            ("Vianda Média", 22.00),
            ("Vianda Grande", 28.00),
            ("Almoço Livre", 24.00),
        ]
        for i, (item1, preco1) in enumerate(comidas):
            button = QPushButton(item1)
            button.clicked.connect(lambda _, nome=item1, valor=preco1: self.adicionar_transacao("entrada", nome, valor))
            comida_layout.addWidget(button, i // 3, i % 3)
        layout.addWidget(comida_group)

    def setup_bebidas(self, layout):
        bebida_group = QGroupBox("Bebidas:")
        bebida_layout = QGridLayout(bebida_group)
        bebidas = [
            ("Água Mineral", 4.00),
            ("Cerveja Latão", 8.00),
            ("Taça de Vinho", 15.00),
            ("Refrigerante 600ML", 8.00),
            ("Refrigerante Lata", 6.00),
            ("Caipirinha Copo", 12.00),
        ]
        for i, (item2, preco2) in enumerate(bebidas):
            button = QPushButton(item2)
            button.clicked.connect(lambda _, nome=item2, valor=preco2: self.adicionar_transacao("entrada", nome, valor))
            bebida_layout.addWidget(button, i // 3, i % 3)
        layout.addWidget(bebida_group)

    def setup_outros(self, layout):
        outros_group = QGroupBox("Outros:")
        outros_layout = QFormLayout(outros_group)
        self.almoco_kg_valor = QLineEdit()
        outros_layout.addRow(QLabel("Almoço KG (R$):"), self.almoco_kg_valor)
        add_almoco_button = QPushButton("Adicionar Almoço KG")
        add_almoco_button.clicked.connect(
            lambda: self.adicionar_transacao("entrada", "Almoço KG", self.get_float_from_input(self.almoco_kg_valor)))
        outros_layout.addWidget(add_almoco_button)

        self.quentinha_kg_valor = QLineEdit()
        outros_layout.addRow(QLabel("Quentinha KG (R$):"), self.quentinha_kg_valor)
        add_quentinha_button = QPushButton("Adicionar Quentinha KG")
        add_quentinha_button.clicked.connect(lambda: self.adicionar_transacao("entrada", "Quentinha KG",
                                                                              self.get_float_from_input(
                                                                                  self.quentinha_kg_valor)))
        outros_layout.addWidget(add_quentinha_button)

        self.conjunto_almocos_cliente = QLineEdit()
        outros_layout.addRow(QLabel("Nome do Cliente:"), self.conjunto_almocos_cliente)
        self.conjunto_almocos_valor = QLineEdit()
        outros_layout.addRow(QLabel("Conjunto de Almoços (R$):"), self.conjunto_almocos_valor)
        add_conjunto_button = QPushButton("Adicionar Pagamento Conjunto de Almoços")
        add_conjunto_button.clicked.connect(self.pagar_conjunto_almocos)
        outros_layout.addWidget(add_conjunto_button)

        layout.addWidget(outros_group)

    def setup_dividas_tab(self):
        layout = QVBoxLayout(self.tab_dividas)
        dividas_group = QGroupBox("Débitos:")
        dividas_layout = QVBoxLayout(dividas_group)

        # Tabela de Dívidas
        self.dividas_table.setColumnCount(3)
        self.dividas_table.setHorizontalHeaderLabels(["Nome", "Valor (R$)", "Status"])
        self.dividas_table.setEditTriggers(QAbstractItemView.NoEditTriggers)  # Evita edição direta na tabela
        dividas_layout.addWidget(self.dividas_table)

        # Adicionar Dívida
        adicionar_divida_group = QGroupBox("Adicionar Débito")
        adicionar_divida_layout = QFormLayout(adicionar_divida_group)
        self.nome_divida_input = QLineEdit()
        self.valor_divida_input = QLineEdit()
        adicionar_divida_button = QPushButton("Adicionar Débito")
        adicionar_divida_button.clicked.connect(self.adicionar_divida)
        adicionar_divida_layout.addRow(QLabel("Nome do Cliente:"), self.nome_divida_input)
        adicionar_divida_layout.addRow(QLabel("Valor do Débito (R$):"), self.valor_divida_input)
        adicionar_divida_layout.addWidget(adicionar_divida_button)

        dividas_layout.addWidget(adicionar_divida_group)

        layout.addWidget(dividas_group)

    def adicionar_divida(self):
        nome = self.nome_divida_input.text().strip()
        valor = self.get_float_from_input(self.valor_divida_input)
        if not nome:
            QMessageBox.warning(self, "Entrada Inválida", "Por favor, insira um nome válido para o débito.")
            return
        if valor <= 0:
            QMessageBox.warning(self, "Entrada Inválida", "Por favor, insira um valor positivo para o débito.")
            return

        # Verifica se já existe uma dívida para o mesmo cliente
        divida_existente = next((d for d in self.dividas if d["nome"] == nome), None)
        if divida_existente:
            divida_existente["valor"] += valor  # Adiciona ao débito existente
            divida_existente["status"] = "Pendente"  # Reseta o status
        else:
            self.dividas.append({"nome": nome, "valor": valor, "status": "Pendente"})

        self.atualizar_dividas()
        self.nome_divida_input.clear()
        self.valor_divida_input.clear()

    def atualizar_dividas(self):
        # Filtrar apenas as dívidas que têm valor maior que 0
        dividas_ativas = [divida for divida in self.dividas if divida["valor"] > 0]

        self.dividas_table.setRowCount(len(dividas_ativas))
        for row, divida in enumerate(dividas_ativas):
            self.dividas_table.setItem(row, 0, QTableWidgetItem(divida["nome"]))
            self.dividas_table.setItem(row, 1, QTableWidgetItem(f"R$ {divida['valor']:.2f}"))
            self.dividas_table.setItem(row, 2, QTableWidgetItem(divida["status"]))

        # Atualiza a lista interna de dívidas para refletir apenas as dívidas ativas
        self.dividas = dividas_ativas

    def adicionar_transacao(self, tipo, nome, valor):
        forma_pagamento = self.forma_pagamento_combo.currentText()
        if forma_pagamento == "Selecione":
            QMessageBox.warning(self, "Forma de Pagamento Inválida",
                                "Por favor, selecione uma forma de pagamento válida.")
            return

        if valor <= 0:
            QMessageBox.warning(self, "Valor Inválido", "Por favor, insira um valor positivo para a transação.")
            return

        if forma_pagamento == "Pagamento de Débito":
            divida_cliente = next((d for d in self.dividas if d["nome"] == nome), None)
            if divida_cliente:
                self.quitar_ou_reduzir_divida(divida_cliente, valor)
            else:
                # Adiciona ao saldo, pois não há débito
                QMessageBox.warning(self, "Forma de Pagamento Inválida",
                                    "Por favor, selecione uma forma de pagamento válida.")
        else:
            # Para outras formas de pagamento, apenas registra a transação
            self.adicionar_transacao(f"{self.data_hora_atual} - ","entrada", f"Pagamento Conjunto de Almoços - {nome} - R$ {valor:.2f} ({forma_pagamento})")

    def pagar_conjunto_almocos(self):
        self.data_hora_atual = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        nome_cliente = self.conjunto_almocos_cliente.text().strip()
        valor_almoco = self.get_float_from_input(self.conjunto_almocos_valor)
        forma_pagamento = self.forma_pagamento_combo.currentText()
        if forma_pagamento == "Selecione":
            QMessageBox.warning(self, "Forma de Pagamento Inválida",
                                "Por favor, selecione uma forma de pagamento válida.")
            return


        if nome_cliente == "" or valor_almoco <= 0:
            QMessageBox.warning(self, "Entrada Inválida",
                                "Por favor, insira um nome e um valor válido para o pagamento.")
            return

        if forma_pagamento == "Pagamento de Débito":
            divida_cliente = next((d for d in self.dividas if d["nome"] == nome_cliente))
            if divida_cliente:
                self.quitar_ou_reduzir_divida(divida_cliente, valor_almoco)
            else:
                QMessageBox.warning(self, "Débito Não Encontrado",
                                    "Não há débitos encontrados para o cliente especificado.")
        else:
            transacao_texto = (f"{self.data_hora_atual} - ","entrada", f"Pagamento Conjunto de Almoços - {nome_cliente} - R$ {valor_almoco:.2f} ({forma_pagamento})")
        self.registrar_transacao_texto(transacao_texto)
    def quitar_ou_reduzir_divida(self, divida_cliente, valor):
        self.data_hora_atual = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        if valor <= divida_cliente["valor"]:
            divida_cliente["valor"] -= valor
            if divida_cliente["valor"] == 0:
                divida_cliente["status"] = "Quitado"
                QMessageBox.information(self, "Débito Quitado", "Dívida foi quitada!")
            else:
                QMessageBox.information(self, "Débito Parcial", "Parte da dívida foi quitada.")
            transacao_texto = f"{self.data_hora_atual} - Pagamento de Débito: {divida_cliente['nome']} - R$ {valor:.2f} (Redução de dívida)"
        else:
            excedente = valor - divida_cliente["valor"]
            self.adicionar_ao_saldo(excedente)
            divida_cliente["valor"] = 0
            divida_cliente["status"] = "Quitado"
            QMessageBox.information(self, "Débito Quitado", "Dívida foi quitada!")
            transacao_texto = f"{self.data_hora_atual} - Pagamento de Débito: {divida_cliente['nome']} - R$ {valor:.2f} (Quitação + Saldo(R$ {excedente:.2f}))"

        self.atualizar_dividas()
        self.registrar_transacao_texto(transacao_texto)


    def registrar_transacao(self, tipo, nome, valor, forma_pagamento):
        self.data_hora_atual = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        if tipo == "entrada":
            self.adicionar_ao_saldo(valor)
            transacao_texto = f"{self.data_hora_atual} - entrada: {nome} - R$ {valor:.2f} ({forma_pagamento})"
        else:
            self.reduzir_saldo(valor)
            transacao_texto = f"{self.data_hora_atual} - saída: {nome} - R$ {valor:.2f} ({forma_pagamento})"

        self.registrar_transacao_texto(transacao_texto)

    def adicionar_ao_saldo(self, valor):
        self.saldo_atual += valor
        self.atualizar_saldo_display()

    def reduzir_saldo(self, valor):
        self.saldo_atual -= valor
        self.atualizar_saldo_display()

    def atualizar_saldo_display(self):
        self.saldo_label.setText(f"Saldo Atual: R$ {self.saldo_atual:.2f}")

    def registrar_transacao_texto(self, texto):
        self.transacoes_text_area.append(texto)
    def get_float_from_input(self, input_field):
        try:
            return float(input_field.text().replace(',', '.'))
        except ValueError:
            return 0.0

    def setup_pagamentos_tab(self):
        layout = QVBoxLayout(self.tab_pagamentos)
        # Seção de pagamento de boleto
        boleto_layout = QFormLayout()
        self.nome_boleto_input = QLineEdit()
        self.valor_boleto_input = QLineEdit()
        pagar_boleto_button = QPushButton("Pagar Boleto")
        pagar_boleto_button.clicked.connect(self.pagar_boleto)
        boleto_layout.addRow(QLabel("Nome do Boleto:"), self.nome_boleto_input)
        boleto_layout.addRow(QLabel("Valor:"), self.valor_boleto_input)
        boleto_layout.addWidget(pagar_boleto_button)
        # Seção de pagamento de fornecedor
        fornecedor_layout = QFormLayout()
        self.nome_fornecedor_input = QLineEdit()
        self.valor_fornecedor_input = QLineEdit()
        pagar_fornecedor_button = QPushButton("Pagar Fornecedor")
        pagar_fornecedor_button.clicked.connect(self.pagar_fornecedor)
        fornecedor_layout.addRow(QLabel("Nome do Fornecedor:"), self.nome_fornecedor_input)
        fornecedor_layout.addRow(QLabel("Valor:"), self.valor_fornecedor_input)
        fornecedor_layout.addWidget(pagar_fornecedor_button)
        # Seção de pagamento de funcionário
        funcionario_layout = QVBoxLayout()
        self.funcionario_select = QComboBox()
        self.funcionario_select.currentIndexChanged.connect(self.mostrar_salario_funcionario)
        self.salario_label = QLabel("Salário: R$ 0,00")
        funcionario_layout.addWidget(QLabel("Selecionar Funcionário:"))
        funcionario_layout.addWidget(self.funcionario_select)
        funcionario_layout.addWidget(self.salario_label)
        adicionar_funcionario_button = QPushButton("Adicionar Funcionário")
        adicionar_funcionario_button.clicked.connect(self.adicionar_funcionario_dialog)
        funcionario_layout.addWidget(adicionar_funcionario_button)
        # Botão para remover funcionário
        remove_funcionario_button = QPushButton("Remover Funcionário")
        remove_funcionario_button.clicked.connect(self.remover_funcionario)
        funcionario_layout.addWidget(remove_funcionario_button)
        # Botão para pagar funcionário
        pagar_funcionario_button = QPushButton("Pagar Funcionário")
        pagar_funcionario_button.clicked.connect(self.pagar_funcionario)
        funcionario_layout.addWidget(pagar_funcionario_button)
        # Carregar funcionários do arquivo
        self.carregar_funcionarios()
        # Seção de despesas extras
        despesas_layout = QFormLayout()
        self.descricao_despesa_input = QLineEdit()
        self.valor_despesa_input = QLineEdit()
        adicionar_despesa_button = QPushButton("Adicionar Despesa Extra")
        adicionar_despesa_button.clicked.connect(self.adicionar_despesa_extra)
        despesas_layout.addRow(QLabel("Descrição da Despesa:"), self.descricao_despesa_input)
        despesas_layout.addRow(QLabel("Valor:"), self.valor_despesa_input)
        despesas_layout.addWidget(adicionar_despesa_button)
        # Filtros de Pesquisa
        filtro_layout = QFormLayout()
        self.tipo_filtro = QComboBox()
        self.tipo_filtro.addItems(["Todos", "Boleto", "Fornecedor", "Funcionário", "Despesa Extra"])
        self.data_filtro = QDateEdit()
        self.data_filtro.setDate(QDate.currentDate())  # Define a data atual como padrão
        self.data_filtro.setCalendarPopup(True)
        aplicar_filtro_button = QPushButton("Aplicar Filtro")
        aplicar_filtro_button.clicked.connect(self.aplicar_filtro)
        filtro_layout.addRow(QLabel("Tipo:"), self.tipo_filtro)
        filtro_layout.addRow(QLabel("Data:"), self.data_filtro)
        filtro_layout.addWidget(aplicar_filtro_button)
        # Histórico de Pagamentos
        self.historial_table = QTableWidget()
        self.historial_table.setColumnCount(5)
        self.historial_table.setHorizontalHeaderLabels(["Tipo", "Nome", "Valor", "Data", "Descrição"])
        self.historial_table.setRowCount(0)  # Começa com uma tabela vazia
        # Layout final

        layout.addLayout(boleto_layout)
        layout.addLayout(fornecedor_layout)
        layout.addLayout(funcionario_layout)
        layout.addLayout(despesas_layout)
        layout.addLayout(filtro_layout)
        layout.addWidget(QLabel("Histórico de Pagamentos"))
        layout.addWidget(self.historial_table)
        self.funcionarios = {}  # Armazena dados dos funcionários

    def pagar_boleto(self):
        self.data_hora_atual = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        nome_boleto = self.nome_boleto_input.text()
        valor_boleto = self.get_float_from_input(self.valor_boleto_input)
        self.adicionar_transacao(f"{self.data_hora_atual} - saída", nome_boleto, valor_boleto)
        self.nome_boleto_input.clear()
        self.valor_boleto_input.clear()

    def pagar_fornecedor(self):
        self.data_hora_atual = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        nome_fornecedor = self.nome_fornecedor_input.text()
        valor_fornecedor = self.get_float_from_input(self.valor_fornecedor_input)
        self.adicionar_transacao(f"{self.data_hora_atual} - saída", nome_fornecedor, valor_fornecedor)
        self.nome_fornecedor_input.clear()
        self.valor_fornecedor_input.clear()

    def adicionar_funcionario_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Adicionar Funcionário")
        layout = QFormLayout(dialog)
        nome_input = QLineEdit()
        salario_input = QLineEdit()
        funcao_input = QLineEdit()
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addRow(QLabel("Nome:"), nome_input)
        layout.addRow(QLabel("Salário:"), salario_input)
        layout.addRow(QLabel("Função:"), funcao_input)
        layout.addWidget(button_box)
        button_box.accepted.connect(
            lambda: self.adicionar_funcionario(nome_input.text(), salario_input.text(), funcao_input.text(), dialog))
        button_box.rejected.connect(dialog.reject)
        dialog.exec_()

    def adicionar_funcionario(self, nome, salario, funcao, dialog):
        # Verifica se o nome e o salário foram fornecidos
        if nome and salario and funcao:
            try:
                # Converte o salário para float para garantir consistência de dados
                salario_float = float(salario)
                salario_formatado = f"R$ {salario_float:.2f}"

                # Adiciona o funcionário ao dicionário de funcionários
                self.funcionarios[nome] = {'salario': salario_formatado, 'funcao': funcao}

                # Adiciona o nome do funcionário ao combobox
                self.funcionario_select.addItem(nome)

                # Fecha o diálogo de entrada de funcionário
                dialog.accept()

                # Salva os dados de funcionários no arquivo CSV
                self._salvar_funcionarios_csv()

            except ValueError:
                print("Erro: Salário deve ser um número.")
        else:
            print("Erro: Todos os campos são obrigatórios.")

    def _salvar_funcionarios_csv(self):
        """Salva os dados de funcionários no arquivo CSV."""
        with open("funcionarios.csv", "w", newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Nome', 'Salario', 'Funcao'])  # Cabeçalho do CSV
            for nome, salario, funcao in self.funcionarios.items():
                writer.writerow([nome['Nome'], salario['Salario'], funcao['Funcao']])

    def carregar_funcionarios(self):
        """Carrega os dados de funcionários do arquivo CSV."""
        try:
            with open("funcionarios.csv", "r", encoding='utf-8') as f:
                reader = csv.DictReader(f)
                self.funcionarios = {}  # Inicializa o dicionário de funcionários
                self.funcionario_select.clear()  # Limpa o combobox

                for row in reader:
                    nome = row['Nome']
                    salario = row['Salario']
                    funcao = row['Funcao']

                    # Adiciona o funcionário ao dicionário de funcionários
                    self.funcionarios = {'Nome': nome, 'Salario': salario, 'Funcao': funcao}

                    # Adiciona o nome do funcionário ao combobox
                    self.funcionario_select.addItem(nome)
        except FileNotFoundError:
            print("Aviso: Arquivo de funcionários não encontrado. Criando um novo.")
            self.funcionarios = {}  # Inicializa o dicionário vazio se o arquivo não existir
        except Exception as e:
            print(f"Erro ao carregar funcionários: {str(e)}")

    def remover_funcionario(self):
        nome = self.funcionario_select.currentText()
        if nome in self.funcionarios:
            del self.funcionarios[nome]
            self.funcionario_select.removeItem(self.funcionario_select.currentIndex())

    def mostrar_salario_funcionario(self):
        nome = self.funcionario_select.currentText()
        salario = self.funcionarios.get(nome, {}).get('salario', 'R$ 0,00')
        self.salario_label.setText(f"Salário: {salario}")

    def pagar_funcionario(self):
        self.data_hora_atual = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        nome_funcionario = self.funcionario_select.currentText()
        if nome_funcionario:
            salario = self.funcionarios.get(nome_funcionario, {}).get('salario', 'R$ 0,00')
            valor = float(salario.replace("R$ ", "").replace(",", "."))
            self.adicionar_transacao(f"{datetime} - saída", nome_funcionario, valor)

    def adicionar_despesa_extra(self):
        self.data_hora_atual = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        descricao = self.descricao_despesa_input.text()
        valor = self.get_float_from_input(self.valor_despesa_input)
        self.adicionar_transacao(f"{self.data_hora_atual} - saída", descricao, valor)
        self.descricao_despesa_input.clear()
        self.valor_despesa_input.clear()

    def aplicar_filtro(self):
        tipo = self.tipo_filtro.currentText()
        data = self.data_filtro.date().toString("dd/MM/yyyy")
        for row in range(self.historial_table.rowCount()):
            item_tipo = self.historial_table.item(row, 0).text()
            item_data = self.historial_table.item(row, 3).text()
            self.historial_table.setRowHidden(row, not (item_tipo == tipo or tipo == "Todos") or item_data != data)

    def get_float_from_input(self, input_field):
        try:
            return float(input_field.text().replace(",", "."))
        except ValueError:
            return 0.0

    def setup_estoque_tab(self):
        layout = QVBoxLayout(self.tab_estoque)
        # Formulário para adicionar itens ao estoque
        form_layout = QFormLayout()
        self.nome_item_input = QLineEdit()
        self.tipo_item_input = QLineEdit()
        self.setor_item_input = QComboBox()
        self.setor_item_input.addItems(['Comidas', 'Bebidas', 'Outros'])
        self.peso_item_input = QLineEdit()
        self.quantidade_item_input = QLineEdit()
        form_layout.addRow("Nome do Item:", self.nome_item_input)
        form_layout.addRow("Tipo do Item:", self.tipo_item_input)
        form_layout.addRow("Setor do Item:", self.setor_item_input)
        form_layout.addRow("Peso do Item:", self.peso_item_input)
        form_layout.addRow("Quantidade:", self.quantidade_item_input)
        # Campo de pesquisa
        self.pesquisar_item_input = QLineEdit()
        self.pesquisar_item_input.setPlaceholderText("Pesquisar por Nome do Item...")
        pesquisar_item_button = QPushButton("Pesquisar")
        pesquisar_item_button.clicked.connect(self.pesquisar_item_estoque)
        # Botões
        add_item_button = QPushButton("Adicionar Item ao Estoque")
        add_item_button.clicked.connect(self.adicionar_item_estoque)
        remove_item_button = QPushButton("Remover Item Selecionado")
        remove_item_button.clicked.connect(self.remover_item_estoque)
        # Tabela de estoque
        self.tabela_estoque = QTableWidget()
        self.tabela_estoque.setColumnCount(6)
        self.tabela_estoque.setHorizontalHeaderLabels(["ID", "Nome", "Tipo", "Setor", "Peso", "Quantidade"])
        # Adicionando widgets ao layout
        layout.addLayout(form_layout)
        layout.addWidget(add_item_button)
        layout.addWidget(remove_item_button)
        # Adicionar widgets de pesquisa
        layout.addWidget(self.pesquisar_item_input)
        layout.addWidget(pesquisar_item_button)
        layout.addWidget(self.tabela_estoque)
        # Carregar itens do banco de dados
        self.carregar_estoque()

    def carregar_estoque(self, filtro=None):
        self.tabela_estoque.setRowCount(0)
        if filtro:
            cursor.execute("SELECT * FROM estoque WHERE nome LIKE %s", ('%' + filtro + '%',))
        else:
            cursor.execute("SELECT * FROM estoque")
        for row_number, row_data in enumerate(cursor.fetchall()):
            self.tabela_estoque.insertRow(row_number)
            for column_number, data in enumerate(row_data):
                self.tabela_estoque.setItem(row_number, column_number, QTableWidgetItem(str(data)))

    def adicionar_item_estoque(self):
        nome_item = self.nome_item_input.text()
        tipo_item = self.tipo_item_input.text()  # Presumindo que este também é um QLineEdit
        setor_item = self.setor_item_input.currentText()  # Usando currentText() para QComboBox
        peso_item = str(self.peso_item_input.text())
        quantidade_item = int(self.quantidade_item_input.text())
        cursor.execute("INSERT INTO estoque (nome, tipo, setor, peso, quantidade) VALUES (%s, %s, %s, %s, %s)",
                       (nome_item, tipo_item, setor_item, peso_item, quantidade_item))
        connection.commit()
        QMessageBox.information(self, "Sucesso", "Item adicionado ao estoque!")
        self.carregar_estoque()

    def remover_item_estoque(self):
        selected_row = self.tabela_estoque.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "Aviso", "Selecione um item para remover!")
            return
        item_id = self.tabela_estoque.item(selected_row, 0).text()
        cursor.execute("DELETE FROM estoque WHERE id = %s", (item_id,))
        connection.commit()
        QMessageBox.information(self, "Sucesso", "Item removido do estoque!")
        self.carregar_estoque()

    def pesquisar_item_estoque(self):
        filtro = self.pesquisar_item_input.text()
        self.carregar_estoque(filtro=filtro)

    def setup_relatorios_tab(self):
        layout = QVBoxLayout(self.tab_relatorios)
       
        # Filtro de Relatórios
        filtro_group = QGroupBox("Filtro de Relatórios")
        filtro_layout = QFormLayout(filtro_group)

        self.periodo_combobox = QComboBox()
        self.periodo_combobox.addItems(["Diário", "Semanal", "Mensal", "Anual"])
        filtro_layout.addRow(QLabel("Período:"), self.periodo_combobox)

        self.data_inicio_input = QDateEdit()
        self.data_inicio_input.setDisplayFormat(str("dd-MM-yyyy"))
        self.data_inicio_input.setCalendarPopup(True)
        self.data_inicio_input.setToolTip("Selecione a data de início")
        filtro_layout.addRow(QLabel("Data de Início:"), self.data_inicio_input)

        self.data_fim_input = QDateEdit()
        self.data_fim_input.setDisplayFormat(str("dd-MM-yyyy"))
        self.data_fim_input.setCalendarPopup(True)
        self.data_fim_input.setToolTip("Selecione a data de fim")
        filtro_layout.addRow(QLabel("Data de Fim:"), self.data_fim_input)

        filtro_group.setLayout(filtro_layout)
        

        # Botões de Exportação
        export_buttons_layout = QVBoxLayout()

        export_txt_button = QPushButton("Exportar para TXT")
        export_txt_button.clicked.connect(self.exportar_relatorio_txt)
        export_buttons_layout.addWidget(export_txt_button)

        export_excel_button = QPushButton("Exportar para Excel")
        export_excel_button.clicked.connect(self.exportar_relatorio_excel)
        export_buttons_layout.addWidget(export_excel_button)

        export_pdf_button = QPushButton("Exportar para PDF")
        export_pdf_button.clicked.connect(self.exportar_relatorio_pdf)
        export_buttons_layout.addWidget(export_pdf_button)

        layout.addLayout(export_buttons_layout)
        layout.addWidget(filtro_group)


    def exportar_relatorio_txt(self):
        periodo = self.periodo_combobox.currentText()
        data_inicio = self.data_inicio_input.date().toString("yyyy-MM-dd")
        data_fim = self.data_fim_input.date().toString("yyyy-MM-dd")

        filename = QFileDialog.getSaveFileName(self, "Salvar Relatório como TXT",
                                               f"Relatório_{periodo}_{data_inicio}_a_{data_fim}.txt",
                                               "Text Files (*.txt)")[0]
        if not filename:
            return

        with open(filename, "w") as file:
            file.write(f"Relatório de {self.nome_restaurante}\n")
            file.write(f"Período: {periodo}\n")
            file.write(f"Data de Início: {data_inicio}\n")
            file.write(f"Data de Fim: {data_fim}\n")
            file.write("=========================================\n")
            for transacao in self.transacoes:
                data_transacao = datetime.strptime(transacao['data_hora'], "%d-%m-%Y %H:%M:%S")
                if data_inicio and data_fim:
                    if not (data_inicio <= data_transacao.strftime("%Y-%m-%d") <= data_fim):
                        continue
                file.write(
                    f"{transacao['data_hora']} - {transacao['tipo']}: {transacao['descricao']} - R$ {transacao['valor']:.2f} | Saldo: R$ {transacao['saldo_atual']:.2f}\n")
            file.write("=========================================\n")
            file.write(f"Total de Transações: {len(self.transacoes)}\n")
            file.write(f"Saldo Final: R$ {self.saldo_atual:.2f}\n")

            if self.saldo_atual > 0:
                file.write("Resultado: Lucro\n")
            elif self.saldo_atual < 0:
                file.write("Resultado: Prejuízo\n")
            else:
                file.write("Resultado: Neutro\n")

        QMessageBox.information(self, "Relatório", f"Relatório exportado com sucesso para '{filename}'.")

    def exportar_relatorio_excel(self):
        periodo = self.periodo_combobox.currentText()
        data_inicio = self.data_inicio_input.date().toPyDate()
        data_fim = self.data_fim_input.date().toPyDate()

        data_inicio_formatted = data_inicio.strftime("%d-%m-%Y") if data_inicio else "início"
        data_fim_formatted = data_fim.strftime("%d-%m-%Y") if data_fim else "fim"
        filename = QFileDialog.getSaveFileName(self, "Salvar Relatório como Excel",
                                               f"Relatório_{periodo}_{data_inicio_formatted}_a_{data_fim_formatted}.xlsx",
                                               "Excel Files (*.xlsx)")[0]
        if not filename:
            return

        data = []
        for transacao in self.transacoes:
            data_transacao = datetime.strptime(transacao['data_hora'], "%d-%m-%Y %H:%M:%S")
            if data_inicio and data_fim:
                if not (data_inicio <= data_transacao.date() <= data_fim):
                    continue
            data.append([
                transacao['data_hora'],
                transacao['tipo'],
                transacao['descricao'],
                transacao['valor'],
                transacao['saldo_atual']
            ])

        df = pd.DataFrame(data, columns=["Data/Hora", "Tipo", "Descrição", "Valor", "Saldo Atual"])
        df.to_excel(filename, index=False)
        QMessageBox.information(self, "Relatório", f"Relatório exportado com sucesso para '{filename}'.")

    def exportar_relatorio_pdf(self):
        periodo = self.periodo_combobox.currentText()
        data_inicio = self.data_inicio_input.date().toPyDate()
        data_fim = self.data_fim_input.date().toPyDate()

        data_inicio_formatted = data_inicio.strftime("%d-%m-%Y") if data_inicio else "início"
        data_fim_formatted = data_fim.strftime("%d-%m-%Y") if data_fim else "fim"
        filename = QFileDialog.getSaveFileName(self, "Salvar Relatório como PDF",
                                               f"Relatório_{periodo}_{data_inicio_formatted}_a_{data_fim_formatted}.pdf",
                                               "PDF Files (*.pdf)")[0]
        if not filename:
            return

        c = canvas.Canvas(filename, pagesize=letter)
        width, height = letter
        c.drawString(72, height - 72, f"Relatório de {self.nome_restaurante}\n")
        c.drawString(72, height - 72, f"Período: {periodo}\n")
        c.drawString(72, height - 72, f"Data de Início: {data_inicio}\n")
        c.drawString(72, height - 72, f"Data de Fim: {data_fim}\n")
        c.drawString(72, height - 100, "=========================================")

        y = height - 120
        for transacao in self.transacoes:
            data_transacao = datetime.strptime(transacao['data_hora'], "%d-%m-%Y %H:%M:%S")
            if data_inicio and data_fim:
                if not (data_inicio <= data_transacao.date() <= data_fim):
                    continue
            c.drawString(72, y,
                         f"{transacao['data_hora']} - {transacao['tipo']}: {transacao['descricao']} - R$ {transacao['valor']:.2f} | Saldo: R$ {transacao['saldo_atual']:.2f}")
            y -= 14
            if y < 72:
                c.showPage()
                y = height - 72

        c.drawString(72, y - 20, "=========================================")
        c.drawString(72, y - 40, f"Total de Transações: {len(self.transacoes)}")
        c.drawString(72, y - 60, f"Saldo Final: R$ {self.saldo_atual:.2f}")

        if self.saldo_atual > 0:
            c.drawString(72, y - 80, "Resultado: Lucro")
        elif self.saldo_atual < 0:
            c.drawString(72, y - 80, "Resultado: Prejuízo")
        else:
            c.drawString(72, y - 80, "Resultado: Neutro")

        c.save()
        QMessageBox.information(self, "Relatório", f"Relatório exportado com sucesso para '{filename}'.")

    def get_float_from_input(self, line_edit):
        try:
            return float(line_edit.text().replace(',', '.'))
        except ValueError:
            QMessageBox.warning(self, "Entrada Inválida", "Por favor, insira um valor numérico válido.")
            return 0.0

    def setup_usuarios_tab(self):
        layout = QVBoxLayout(self.tab_usuarios)
        self.usuarios_table = QTableWidget()
        self.usuarios_table.setColumnCount(3)
        self.usuarios_table.setHorizontalHeaderLabels(["Nome", "Tipo", "Ações"])
        layout.addWidget(self.usuarios_table)
        self.listar_usuarios()
        # Adicionar Usuário
        self.adicionar_usuario_button = QPushButton("Adicionar Usuário")
        self.adicionar_usuario_button.clicked.connect(self.adicionar_usuario)
        layout.addWidget(self.adicionar_usuario_button)
        # Remover Usuário
        self.remover_usuario_button = QPushButton("Remover Usuário")
        self.remover_usuario_button.clicked.connect(self.remover_usuario)
        layout.addWidget(self.remover_usuario_button)

    def listar_usuarios(self):
        self.usuarios_table.setRowCount(0)
        usuarios = listar_usuarios_bd()
        for i, (nome_usuario, nivel_usuario) in enumerate(usuarios):
            if self.tipo_usuario == "admin" or self.tipo_usuario == "gerente":
                self.usuarios_table.insertRow(i)
                self.usuarios_table.setItem(i, 0, QTableWidgetItem(nome_usuario))
                self.usuarios_table.setItem(i, 1, QTableWidgetItem(nivel_usuario))
                acoes_button = QPushButton("Remover")
                acoes_button.clicked.connect(lambda _, row=i: self.remover_usuario_confirmacao(row))
                self.usuarios_table.setCellWidget(i, 2, acoes_button)

    def adicionar_usuario(self):
        if self.tipo_usuario == "admin":
            dialog = QDialog(self)
            dialog.setWindowTitle("Adicionar Usuário")
            layout = QFormLayout(dialog)
            nome_usuario = QLineEdit()
            senha_usuario = QLineEdit()
            tipo_usuario = QComboBox()
            tipo_usuario.addItems(["admin", "gerente", "cozinha", "garcom"])
            layout.addRow(QLabel("Nome:"), nome_usuario)
            layout.addRow(QLabel("Senha:"), senha_usuario)
            layout.addRow(QLabel("Tipo:"), tipo_usuario)
            button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
            button_box.accepted.connect(
                lambda: self.adicionar_usuario_confirmacao(nome_usuario.text(), senha_usuario.text(),
                                                           tipo_usuario.currentText(), dialog))
            button_box.rejected.connect(dialog.reject)
            layout.addWidget(button_box)
            dialog.exec_()
        else:
            QMessageBox.warning(self, "Permissão Negada", "Você não tem permissão para adicionar usuários.")

    def adicionar_usuario_confirmacao(self, nome_usuario, senha_usuario, nivel_usuario, dialog):
        if self.tipo_usuario == "admin":
            adicionar_usuario_bd(nome_usuario, senha_usuario, nivel_usuario)
            self.listar_usuarios()
            dialog.accept()

    def remover_usuario(self):
        if self.tipo_usuario == "admin":
            row = self.usuarios_table.currentRow()
            if row >= 0:
                nome_usuario = self.usuarios_table.item(row, 0).text()
                if nome_usuario != "admin" or self.tipo_usuario == "admin":
                    remover_usuario_bd(nome_usuario)
                    self.listar_usuarios()
                else:
                    QMessageBox.warning(self, "Permissão Negada", "Você não pode remover um usuário Admin.")
        else:
            QMessageBox.warning(self, "Permissão Negada", "Você não tem permissão para remover usuários.")

    def remover_usuario_confirmacao(self, row):
        if self.tipo_usuario == "admin":
            nome_usuario = self.usuarios_table.item(row, 0).text()
            if nome_usuario != "admin" or self.tipo_usuario == "admin":
                reply = QMessageBox.question(self, 'Confirmar Remoção',
                                             f"Tem certeza de que deseja remover {nome_usuario}?",
                                             QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if reply == QMessageBox.Yes:
                    remover_usuario_bd(nome_usuario)
                    self.listar_usuarios()
            else:
                QMessageBox.warning(self, "Permissão Negada", "Você não pode remover um usuário Admin.")
        else:
            QMessageBox.warning(self, "Permissão Negada", "Você não tem permissão para remover usuários.")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    while True:
        login_dialog = LoginDialog()  # Cria a janela de login
        if login_dialog.exec_() == QDialog.Accepted:
            nome_usuario, senha_usuario = login_dialog.get_user_credentials()
            if autenticar_usuario(nome_usuario, senha_usuario):
                tipo_usuario = obter_tipo_usuario(nome_usuario)
                main_window = SistemaVendas(tipo_usuario, nome_usuario, login_dialog)
                main_window.show()
                app.exec_()
                if not main_window.isVisible():
                    continue  # Volta para o início do loop para mostrar o login novamente
            else:
                print("Nome de usuário ou senha inválidos.")
                break  # Opcional: sai do loop e encerra o aplicativo se a autenticação falhar
        else:
            break  # Sai do loop se o usuário cancelar o diálogo de login
    sys.exit()
