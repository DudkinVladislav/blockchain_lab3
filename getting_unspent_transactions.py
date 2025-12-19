from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
import json
from decimal import Decimal


class DigitalAssetPortfolioInspector:
    def __init__(self, node_user, node_pass, node_ip='127.0.0.1', node_port=8332, portfolio_label=''):
        """
        Инициализация подключения к узлу Bitcoin

        Args:
            node_user: Имя пользователя узла
            node_pass: Пароль узла
            node_ip: IP адрес узла
            node_port: Порт узла
            portfolio_label: Метка портфеля (для мультикошельковой конфигурации)
        """
        self.node_user = node_user
        self.node_pass = node_pass
        self.node_ip = node_ip
        self.node_port = node_port
        self.portfolio_label = portfolio_label

        # Формируем строку подключения
        if portfolio_label:
            self.connection_string = f"http://{node_user}:{node_pass}@{node_ip}:{node_port}/wallet/{portfolio_label}"
        else:
            self.connection_string = f"http://{node_user}:{node_pass}@{node_ip}:{node_port}/"

        self.node_client = None

    def establish_link(self):
        """Установить соединение с узлом"""
        try:
            self.node_client = AuthServiceProxy(self.connection_string)
            # Тестируем подключение
            blockchain_data = self.node_client.getblockchaininfo()
            print(f"✓ Успешное подключение к сети: {blockchain_data['chain']}")
            print(f"✓ Текущая высота: {blockchain_data['blocks']}")
            return True
        except Exception as error:
            print(f"✗ Ошибка подключения: {error}")
            return False

    def calculate_unspent_balance(self, target_address):
        """
        Рассчитать сумму всех непотраченных выходов для адреса

        Args:
            target_address: Целевой адрес

        Returns:
            dict: {'total_btc': Decimal, 'total_sats': int, 'unspent_count': int, 'unspent_list': list}
        """
        if not self.node_client:
            print("Сначала выполните подключение через establish_link()")
            return None

        try:
            # Запрашиваем непотраченные транзакции
            unspent_transactions = self.node_client.listunspent(0, 9999999, [target_address])

            cumulative_sats = 0
            unspent_items = []

            for transaction in unspent_transactions:
                # Подтверждаем принадлежность адресу
                if transaction['address'] == target_address:
                    sats_value = int(Decimal(transaction['amount']) * Decimal('1e8'))
                    cumulative_sats += sats_value

                    transaction_record = {
                        'transaction_id': transaction['txid'],
                        'output_index': transaction['vout'],
                        'btc_value': float(transaction['amount']),
                        'sats_value': sats_value,
                        'confirmations': transaction['confirmations'],
                        'spendable': transaction['spendable'],
                        'secure': transaction.get('safe', True)
                    }
                    unspent_items.append(transaction_record)

            total_btc = Decimal(cumulative_sats) / Decimal('1e8')

            report = {
                'address': target_address,
                'total_btc': total_btc,
                'total_sats': cumulative_sats,
                'unspent_count': len(unspent_items),
                'unspent_list': unspent_items
            }

            return report

        except JSONRPCException as rpc_error:
            print(f"✗ Ошибка RPC: {rpc_error}")
            return None
        except Exception as error:
            print(f"✗ Общая ошибка: {error}")
            return None

    def fetch_portfolio_total(self):
        """Получить общий баланс портфеля"""
        try:
            portfolio_total = self.node_client.getbalance()
            return {
                'portfolio_btc': Decimal(portfolio_total),
                'portfolio_sats': int(Decimal(portfolio_total) * Decimal('1e8'))
            }
        except Exception as error:
            print(f"✗ Ошибка запроса баланса: {error}")
            return None

    def enumerate_addresses(self):
        """Получить перечень адресов в портфеле"""
        try:
            address_collection = []

            # Получаем адреса с дополнительной информацией
            address_data = self.node_client.listreceivedbyaddress(0, True)
            for addr_entry in address_data:
                address_collection.append({
                    'address': addr_entry['address'],
                    'balance': addr_entry['amount'],
                    'confirmations': addr_entry['confirmations']
                })

            return address_collection
        except Exception as error:
            print(f"✗ Ошибка получения адресов: {error}")
            return []


def display_balance_report(report_data):
    """Форматированный вывод результатов"""
    if not report_data:
        print("Отсутствуют данные для отображения")
        return

    print("\n" + "=" * 60)
    print(f"Анализ непотраченных выходов для адреса: {report_data['address']}")
    print("=" * 60)
    print(f"Всего непотраченных выходов: {report_data['unspent_count']}")
    print(f"Общий баланс: {report_data['total_btc']:.8f} BTC")
    print(f"Общий баланс: {report_data['total_sats']:,} сатоши")
    print("-" * 60)

    if report_data['unspent_list']:
        print("\nДетализация выходов:")
        print("-" * 60)
        for idx, utxo in enumerate(report_data['unspent_list'], 1):
            print(f"{idx}. Идентификатор: {utxo['transaction_id'][:20]}...")
            print(f"   Индекс выхода: {utxo['output_index']}")
            print(f"   Сумма: {utxo['btc_value']:.8f} BTC ({utxo['sats_value']:,} сатоши)")
            print(f"   Подтверждений: {utxo['confirmations']}")
            print(f"   Доступность: {'Да' if utxo['spendable'] else 'Нет'}")
            print("-" * 40)
    else:
        print("Непотраченные выходы не обнаружены")


def execute_analysis():
    # Параметры подключения к тестовой сети
    NODE_USERNAME = '***'
    NODE_CREDENTIAL = '***'
    NODE_ADDRESS = '127.0.0.1'
    NODE_CONNECTION_PORT = 48332
    PORTFOLIO_IDENTIFIER = 'testwallet'

    ANALYZED_ADDRESS = 'tb1q2m5g3e7pm6k2pgh44kaglk4m0xw3xgpjgprf3w'

    print("Анализатор непотраченных транзакций Bitcoin")
    print("=" * 60)

    # Создаем экземпляр анализатора
    inspector = DigitalAssetPortfolioInspector(
        node_user=NODE_USERNAME,
        node_pass=NODE_CREDENTIAL,
        node_ip=NODE_ADDRESS,
        node_port=NODE_CONNECTION_PORT,
        portfolio_label=PORTFOLIO_IDENTIFIER
    )

    # Устанавливаем соединение
    if not inspector.establish_link():
        print("Не удалось подключиться к узлу Bitcoin")
        return

    # Запрашиваем общий баланс
    portfolio_total = inspector.fetch_portfolio_total()
    if portfolio_total:
        print(f"Суммарный баланс портфеля: {portfolio_total['portfolio_btc']:.8f} BTC")

    # Анализируем указанный адрес
    print(f"\nАнализ адреса: {ANALYZED_ADDRESS}")
    analysis_result = inspector.calculate_unspent_balance(ANALYZED_ADDRESS)

    # Отображаем результаты
    if analysis_result:
        display_balance_report(analysis_result)

        # Сохраняем в файл
        with open('utxo_report.json', 'w') as output_file:
            json.dump({
                'address': analysis_result['address'],
                'total_btc': str(analysis_result['total_btc']),
                'total_sats': analysis_result['total_sats'],
                'unspent_count': analysis_result['unspent_count'],
                'unspent_list': analysis_result['unspent_list']
            }, output_file, indent=2)
        print("\nРезультаты сохранены в utxo_report.json")
    else:
        print("Не удалось получить данные по непотраченным выходам")


if __name__ == "__main__":
    execute_analysis()
