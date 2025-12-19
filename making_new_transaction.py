from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
from decimal import Decimal
import hashlib
import struct


class BitcoinTransactionCreator:
    def __init__(self, node_user, node_pass, node_host='127.0.0.1', node_port=48332, wallet_id=''):
        """
        Инициализация подключения к узлу Bitcoin

        Args:
            node_user: Имя пользователя RPC
            node_pass: Пароль RPC
            node_host: Хост узла
            node_port: Порт узла
            wallet_id: Идентификатор кошелька
        """
        self.node_user = node_user
        self.node_pass = node_pass
        self.node_host = node_host
        self.node_port = node_port
        self.wallet_id = wallet_id

        if wallet_id:
            self.connection_string = f"http://{node_user}:{node_pass}@{node_host}:{node_port}/wallet/{wallet_id}"
        else:
            self.connection_string = f"http://{node_user}:{node_pass}@{node_host}:{node_port}/"

        self.node_client = None

    def connect_to_node(self):
        """Установить соединение с узлом"""
        try:
            self.node_client = AuthServiceProxy(self.connection_string)
            blockchain_info = self.node_client.getblockchaininfo()
            print(f"✓ Подключено к сети: {blockchain_info['chain']}")
            return True
        except Exception as error:
            print(f"✗ Ошибка подключения: {error}")
            return False

    def calculate_transaction_fee(self, tx_size_bytes, sat_per_byte):
        """
        Рассчитать комиссию транзакции

        Args:
            tx_size_bytes: Размер транзакции в байтах
            sat_per_byte: Комиссия в сатоши за байт

        Returns:
            int: Комиссия в сатоши
        """
        return tx_size_bytes * sat_per_byte

    def create_raw_transaction(self, inputs_list, outputs_dict):
        """
        Создать сырую транзакцию

        Args:
            inputs_list: Список входов [{"txid": "...", "vout": n}]
            outputs_dict: Словарь выходов {"address": amount_btc}

        Returns:
            str: Хеш сырой транзакции или None при ошибке
        """
        if not self.node_client:
            print("Сначала подключитесь к узлу")
            return None

        try:
            raw_tx = self.node_client.createrawtransaction(inputs_list, outputs_dict)
            return raw_tx
        except JSONRPCException as rpc_error:
            print(f"✗ Ошибка создания транзакции: {rpc_error}")
            return None

    def sign_transaction(self, raw_tx_hex):
        """
        Подписать транзакцию

        Args:
            raw_tx_hex: HEX сырой транзакции

        Returns:
            dict: Подписанная транзакция или None при ошибке
        """
        try:
            signed_tx = self.node_client.signrawtransactionwithwallet(raw_tx_hex)
            return signed_tx
        except JSONRPCException as rpc_error:
            print(f"✗ Ошибка подписания: {rpc_error}")
            return None

    def broadcast_transaction(self, signed_tx_hex):
        """
        Отправить транзакцию в сеть

        Args:
            signed_tx_hex: HEX подписанной транзакции

        Returns:
            str: Хеш транзакции или None при ошибке
        """
        try:
            tx_hash = self.node_client.sendrawtransaction(signed_tx_hex)
            return tx_hash
        except JSONRPCException as rpc_error:
            print(f"✗ Ошибка отправки: {rpc_error}")
            return None

    def get_unspent_outputs(self, min_confirmations=1, max_confirmations=9999999, addresses=None):
        """
        Получить непотраченные выходы

        Args:
            min_confirmations: Минимальное количество подтверждений
            max_confirmations: Максимальное количество подтверждений
            addresses: Список адресов для фильтрации

        Returns:
            list: Список непотраченных выходов
        """
        try:
            if addresses:
                unspent = self.node_client.listunspent(min_confirmations, max_confirmations, addresses)
            else:
                unspent = self.node_client.listunspent(min_confirmations, max_confirmations)
            return unspent
        except JSONRPCException as rpc_error:
            print(f"✗ Ошибка получения UTXO: {rpc_error}")
            return []

    def estimate_transaction_size(self, input_count, output_count, is_segwit=True):
        """
        Оценить размер транзакции

        Args:
            input_count: Количество входов
            output_count: Количество выходов
            is_segwit: Используются ли SegWit входы

        Returns:
            int: Примерный размер в байтах
        """
        # Базовые размеры компонентов
        BASE_TX_SIZE = 10
        INPUT_SIZE_NON_SEGWIT = 148
        INPUT_SIZE_SEGWIT = 68
        OUTPUT_SIZE = 34

        input_size = INPUT_SIZE_SEGWIT if is_segwit else INPUT_SIZE_NON_SEGWIT
        estimated_size = BASE_TX_SIZE + (input_count * input_size) + (output_count * OUTPUT_SIZE)

        return estimated_size

    def select_inputs_for_amount(self, target_amount_btc, unspent_outputs):
        """
        Выбрать входы для указанной суммы

        Args:
            target_amount_btc: Целевая сумма в BTC
            unspent_outputs: Список непотраченных выходов

        Returns:
            tuple: (список выбранных входов, общая сумма, сдача)
        """
        target_sats = int(Decimal(target_amount_btc) * Decimal('1e8'))
        selected_inputs = []
        total_sats = 0

        # Сортируем по количеству подтверждений (сначала более подтвержденные)
        sorted_outputs = sorted(unspent_outputs, key=lambda x: x['confirmations'], reverse=True)

        for output in sorted_outputs:
            if total_sats >= target_sats:
                break

            output_sats = int(Decimal(output['amount']) * Decimal('1e8'))
            selected_inputs.append({
                "txid": output['txid'],
                "vout": output['vout']
            })
            total_sats += output_sats

        if total_sats < target_sats:
            return [], 0, 0

        change_sats = total_sats - target_sats
        return selected_inputs, total_sats, change_sats


def create_and_send_transaction():
    """Пример создания и отправки транзакции"""
    # Параметры подключения
    NODE_USERNAME = 'username'
    NODE_PASSWORD = 'password'
    NODE_HOST = '127.0.0.1'
    NODE_PORT = 48332
    WALLET_NAME = 'testwallet'

    # Параметры транзакции
    RECIPIENT_ADDRESS = 'bc1qaddresshere'
    AMOUNT_BTC = 0.001
    FEE_RATE = 2  # сатоши за байт

    print("Создание транзакции Bitcoin")
    print("=" * 50)

    # Инициализация
    tx_creator = BitcoinTransactionCreator(
        node_user=NODE_USERNAME,
        node_pass=NODE_PASSWORD,
        node_host=NODE_HOST,
        node_port=NODE_PORT,
        wallet_id=WALLET_NAME
    )

    # Подключение
    if not tx_creator.connect_to_node():
        return

    # Получаем непотраченные выходы
    unspent_outputs = tx_creator.get_unspent_outputs()
    if not unspent_outputs:
        print("Нет доступных непотраченных выходов")
        return

    # Выбираем входы для нужной суммы
    inputs, total_sats, change_sats = tx_creator.select_inputs_for_amount(AMOUNT_BTC, unspent_outputs)
    if not inputs:
        print("Недостаточно средств")
        return

    # Оцениваем размер транзакции
    output_count = 2 if change_sats > 0 else 1
    estimated_size = tx_creator.estimate_transaction_size(len(inputs), output_count)

    # Рассчитываем комиссию
    fee_sats = tx_creator.calculate_transaction_fee(estimated_size, FEE_RATE)

    # Проверяем, хватает ли средств с учетом комиссии
    amount_sats = int(Decimal(AMOUNT_BTC) * Decimal('1e8'))
    if total_sats < (amount_sats + fee_sats):
        print(f"Недостаточно средств. Нужно: {amount_sats + fee_sats} сатоши, есть: {total_sats}")
        return

    # Пересчитываем сдачу с учетом комиссии
    change_sats = total_sats - amount_sats - fee_sats

    # Формируем выходы
    outputs = {RECIPIENT_ADDRESS: Decimal(AMOUNT_BTC)}
    if change_sats > 0:
        # Получаем адрес для сдачи (первый адрес из кошелька)
        try:
            addresses = tx_creator.node_client.listreceivedbyaddress(0, True)
            if addresses:
                change_address = addresses[0]['address']
                outputs[change_address] = Decimal(change_sats) / Decimal('1e8')
        except:
            print("Не удалось получить адрес для сдачи")
            return

    # Создаем сырую транзакцию
    print("Создание сырой транзакции...")
    raw_tx = tx_creator.create_raw_transaction(inputs, outputs)
    if not raw_tx:
        return

    # Подписываем транзакцию
    print("Подписание транзакции...")
    signed_tx = tx_creator.sign_transaction(raw_tx)
    if not signed_tx or not signed_tx.get('complete'):
        print("Ошибка подписания транзакции")
        return

    # Отправляем транзакцию
    print("Отправка транзакции в сеть...")
    tx_hash = tx_creator.broadcast_transaction(signed_tx['hex'])

    if tx_hash:
        print(f"✓ Транзакция успешно отправлена!")
        print(f"Хеш транзакции: {tx_hash}")
        print(f"Сумма: {AMOUNT_BTC} BTC")
        print(f"Комиссия: {fee_sats} сатоши ({Decimal(fee_sats) / Decimal('1e8'):.8f} BTC)")
        print(f"Размер: ~{estimated_size} байт")
    else:
        print("✗ Не удалось отправить транзакцию")


if __name__ == "__main__":
    create_and_send_transaction()
