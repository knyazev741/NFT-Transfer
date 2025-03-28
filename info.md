Автоматизация перевода NFT и TON в сети TON

Введение и постановка задачи

Пользователю необходимо автоматизировать вывод всех NFT-токенов и всех Toncoin (TON) с нескольких кошельков в сети TON. Кошельки используются через приложения ToneKeeper и MyTonWallet, при этом каждый кошелек определяется своей seed-фразой (мнемонической фразой восстановления). Требуется написать Python-скрипт, который:
	•	Подключается к каждому кошельку по его seed-фразе, определяя соответствующий адрес кошелька и тип смарт-контракта кошелька (ToneKeeper и MyTonWallet могут использовать разные версии стандартных wallet-контрактов).
	•	С помощью API (например, TON API от tonapi.io) получает список всех NFT, принадлежащих данному адресу кошелька ￼.
	•	Определяет формат и стандарт NFT коллекции Lost Dogs (Vault) – эти NFT выпущены через механизм “Vault”, но соответствуют стандарту NFT на TON (TEP-62/64, ранее известный как TIP-4) ￼. Это означает, что их перевод осуществляется стандартным методом transfer с опкодом 0x5FCC3D14 ￼, как и для любых других TON NFT.
	•	Переводит все NFT-токены с кошелька на указанный целевой адрес (например, адрес основного кошелька пользователя). Для каждого NFT формируется внутреннее сообщение перевода на новый адрес владельца. Согласно стандарту TON NFT, в тело сообщения включается специальный опкод и параметры: новый владелец, адрес для ответа и опционально пользовательские данные ￼.
	•	Примечание: NFT из коллекции Lost Dogs (Vault) содержат залоченные токены WOOF, но это не влияет на процедуру их передачи – они полностью соответствуют стандарту TEP-62/64. После передачи NFT новый владелец сможет разблокировать токены через контракт Vault (при наступлении срока) без участия исходного владельца.
	•	После успешной отправки всех NFT, скрипт отправляет весь оставшийся баланс TON с данного кошелька на тот же целевой адрес (за вычетом комиссии за эту финальную транзакцию). В итоге каждый кошелек будет опустошен, а все ценности (NFT и монеты TON) переведены на целевой адрес.
	•	Учитывает возможные различия в кошельках ToneKeeper и MyTonWallet. Эти приложения могут использовать разные версии стандартных кошельковых смарт-контрактов TON (например, v3R2, v4R2 или даже v5). От версии кошелька зависит порядок формирования адреса и порядок подписания транзакций. Скрипт должен правильно определить версию кошелька по seed-фразе или предоставить настройку, чтобы верно подписывать переводы.
	•	Ведет лог операций для каждого кошелька. В логе по каждому кошельку должны фиксироваться:
	•	Адрес кошелька и, при необходимости, тип/версия кошелькового контракта.
	•	Список NFT, которые удалось отправить (например, их адреса или идентификаторы коллекций).
	•	Суммарное количество TON, отправленных с кошелька (и сколько осталось неиспользованным, если что-то не удалось).
	•	Информация об ошибках или NFT, которые не удалось отправить (например, если на комиссии не хватило средств или произошла другая ошибка).

Ниже приводится описание ключевых моментов реализации и полный код скрипта на Python, удовлетворяющего указанным требованиям.

Подключение к кошелькам по seed-фразам

Первый шаг – получение доступа к кошельку по известной мнемонической фразе. В TON каждая seed-фраза соответствует детерминированному набору ключей (BIP-39), из которых формируется публичный/приватный ключ ED25519, а затем разворачивается смарт-контракт кошелька. При этом адрес кошелька зависит как от публичного ключа, так и от версии кошелькового контракта (wallet code). ToneKeeper и MyTonWallet могут использовать разные версии: например, MyTonWallet обычно создаёт кошельки версии V3R2, тогда как ToneKeeper (особенно новые версии) по умолчанию используют V4R2 или даже V5 ￼.

Алгоритм определения адреса кошелька:
	•	Для каждой seed-фразы скрипт генерирует ED25519 ключи. Это можно сделать с помощью библиотек (например, tonsdk или ton), которые поддерживают импорт кошельков по мнемонике.
	•	Затем определяется версия кошелькового контракта. Если известно заранее (например, пользователь может указать, что seed1 – ToneKeeper (v4) и seed2 – MyTonWallet (v3)), то используются эти версии. Иначе скрипт может попытаться автоматически определить:
	•	Сгенерировать адрес для версии V3R2 и для V4R2 и проверить по блокчейну, какой из них активен и имеет баланс или NFT. Например, через TON API можно запросить информацию об аккаунте ￼. Активный адрес с балансом, скорее всего, соответствует правильной версии.
	•	Также можно ориентироваться на длину seed: обе используют 24 слова обычно, так что длина фразы не отличает версии. Поэтому лучше проверить наличие средств/NFT по адресу.
	•	Учесть, что версии отличаются форматом “seqno” (счетчика транзакций). V3 и V4 – стандартные одноключевые кошельки: у них есть метод seqno (номер очередной внешней транзакции) ￼. У V5 (новый Wallet v5 от команды Tonkeeper) также есть свои особенности (поддержка “gasless” и пр.), но для целей вывода средств он работает похоже, с той разницей, что V5 может потребовать иной подход к отправке. В данной задаче будем считать, что используемые кошельки – стандартные V3R2 или V4R2, поскольку они наиболее распространены ￼.

После определения версии кошелька скрипт получает объект кошелька, с которым можно работать (получать баланс, подписывать и отправлять транзакции).

Получение списка NFT через TON API

Чтобы вывести все NFT, нужно узнать, какие NFT принадлежат адресу кошелька. Для этого удобно воспользоваться TON API (TonAPI) – это REST/GraphQL API, предоставляющий индексированную информацию по аккаунтам TON. В частности, TonAPI имеет метод getAccountNftItems, который возвращает все NFT-токены, принадлежащие заданному адресу ￼.

Скрипт делает запрос вида:

GET https://tonapi.io/v2/accounts/{ADDRESS}/nfts?indirect_ownership=false

с заголовком авторизации (необходим API-ключ TonAPI). Параметр indirect_ownership=false означает, что будут перечислены только NFT, непосредственно находящиеся на кошельке (то есть не учтутся NFT, переданные на рынки или в смарт-контракты продажи) ￼. Это соответствует нашим целям – нужно вывести лишь те NFT, что лежат на кошельке. API TonAPI вернет JSON со списком NFT (каждый NFT характеризуется адресом своего смарт-контракта, идентификатором коллекции, названием и пр.).

Далее скрипт извлекает из этого списка адреса всех NFT и, при необходимости, дополнительную информацию. Например, для логов можно сохранить имя коллекции или индекс NFT.

Особый интерес представляет NFT коллекция Lost Dogs: Vault – в задаче явно упомянуто “NFT Lost Docks (выпущенные через Vault)”. Судя по описанию, речь идет о коллекции Lost Dogs: Vaults, где каждый NFT содержит 50,000 залоченных токенов $WOOF (по механике “vault”) ￼. Эти NFT – обычные TON NFT стандарта TEP-62/64, просто в их смарт-контрактах прописана логика хранения токенов до определенной даты. TonAPI вернет их так же, как и любые другие NFT. Скрипт может по адресу NFT или по коллекции определить, что это Lost Dogs (например, по имени коллекции или известному адресу коллекционного контракта), но для процесса передачи это не требуется. Однако, стоит знать, что формат у них стандартный, то есть передаваться они будут обычным методом transfer.

Стандарт NFT на TON (Lost Dogs Vault NFT)

TON внедрил стандарт NFT, описанный в предложениях TEP-62 и TEP-64 (ранее известные как TIP-4.1/4.2). Согласно этому стандарту, у каждого NFT есть отдельный смарт-контракт, а коллекция играет роль индекса ￼. Чтобы передать NFT, текущий владелец должен отправить внутреннее сообщение на адрес NFT-контракта с определенным набором параметров. В исходном коде стандартного NFT этот метод имеет сигнатуру:

transfer#5fcc3d14 
    query_id:uint64 
    new_owner:MsgAddress 
    response_destination:MsgAddress 
    custom_payload:(Maybe ^Cell)
    ...

Здесь #5fcc3d14 – это уникальный опкод операции transfer (первые 32 бита тела сообщения) ￼. Далее передаются:
	•	new_owner – адрес нового владельца NFT (тот самый адрес, на который мы переводим токен),
	•	response_destination – адрес, на который NFT контракт отправит подтверждение (обычно это тоже адрес старого владельца, либо можно указать адрес-заглушку),
	•	custom_payload – опциональные данные (в нашем случае не нужны, можно передать пустую ячейку).

Важно: При отправке NFT принято прикреплять небольшую сумму TON (0.01–0.05 TON) в качестве пересылаемого значения ￼. Это делается для того, чтобы смарт-контракт NFT смог выслать уведомление новому владельцу о поступлении NFT (например, в виде внутреннего сообщения “вы получили NFT”). Если отправить совсем 0, новый владелец может не получить уведомления о трансфере ￼. В нашем скрипте при формировании перевода каждого NFT мы будем прикреплять ~0.05 TON – этого достаточно, чтобы покрыть комиссии исполнения и уведомить получателя.

NFT коллекция Lost Dogs: Vaults следует этому же стандарту. Хотя каждый такой NFT “содержит” токены WOOF, на передачу это не влияет – передача выполняется стандартным сообщением transfer с вышеописанными параметрами. После смены владельца залоченные токены остаются привязаны к NFT, и новый владелец при наступлении времени разблокировки сможет вызвать функцию “claim” (например, через маркетплейс или напрямую), которая выпустит эти токены на его адрес. Для нашего скрипта достаточно корректно перевести NFT; разлочка WOOF произойдет уже вне рамок данной задачи.

Отправка всех NFT на указанный адрес

Скрипт, получив список NFT-адресов, для каждого NFT выполняет следующую последовательность:
	1.	Подготовка сообщения transfer: формируется payload (полезная нагрузка) с опкодом 0x5fcc3d14 и параметрами new_owner = <целевой адрес>, response_destination = <адрес нашего кошелька> (можно указать тот же исходный кошелек или, например, адрес получателя – в нашем случае критично лишь то, чтобы это поле было валидным адресом; обычно ставят свой же адрес, чтобы в случае ошибки NFT вернулся). Мы не передаем custom_payload, оставляя его пустым. Создание такого payload можно сделать вручную через тоновские библиотеки. В Python доступны, например, tonsdk (низкоуровневая) или TonTools. В нашем решении мы воспользуемся библиотекой TON SDK for Python (tonsdk), у которой есть готовый метод NFTItem().create_transfer_body(new_owner_address) ￼ – он возвращает корректно сформированное тело сообщения для transfer.
	2.	Подпись и отправка сообщения: для отправки внутрь блокчейна нам нужно подписать внешнее сообщение кошелька, которое при выполнении создает внутреннее сообщение с указанным payload на адрес NFT. Стандартные кошельки TON позволяют отправлять такие сообщения. Мы используем функции кошелька для формирования перевода:
	•	Получаем текущий seqno кошелька (порядковый номер внешней транзакции). Это можно сделать либо запросом runMethod у самого кошелька, либо с помощью SDK. В нашем скрипте мы запросим seqno через TonCenter API (метод getAccount или runMethod seqno) перед каждой отправкой.
	•	Формируем внешний перевод: для кошельков V3/V4 нужно указать destination (адрес NFT), сумму (в нанотоннах) и payload. Сумма будет равна ~0.05 TON (50000000 нанотонн), как решили выше. Библиотека tonsdk предоставляет метод wallet.create_transfer_message(dest, value, seqno, payload=...) ￼, возвращающий структуру сообщения.
	•	Подписываем сообщение нашим приватным ключом и сериализуем его в BOC (Bag of Cells) – бинарное представление сообщения. Затем отправляем этот BOC в сеть. Для отправки можно использовать либо TonCenter API (метод sendBoc), либо TonAPI (метод /v2/blockchain/message для отправки сообщения ￼). В нашем скрипте будем использовать TonCenter.
	•	После отправки желательно подождать подтверждения или проверить, что транзакция прошла. Но чтобы не задерживать выполнение (особенно если много кошельков), можно сразу переходить к следующей NFT, а результат записывать в лог. Мы будем отслеживать ответ API: если он вернул ошибку, зафиксируем неудачу для данного NFT.
	3.	Повторить для всех NFT: скрипт в цикле отправляет каждый NFT. Для каждого увеличиваем seqno (после каждой успешной отправки кошелек увеличивает свой внутренний счетчик на 1). Также уменьшается баланс Toncoin на кошельке (примерно на 0.05 TON + комиссия за каждую отправку).

В случае ошибки (например, недостаточно TON для оплаты комиссии перевода NFT) скрипт логирует, что данный NFT не удалось отправить. В логах можно указать причину (например, ошибка API или низкий баланс).

Отправка оставшихся TON (Toncoin)

Когда все NFT обработаны, на кошельке остаются только монеты TON (если вообще остались – отправка NFT стоила комиссию, плюс прикрепленные 0.05 TON фактически перейдут на целевой адрес через уведомления). Теперь нужно вывести все оставшиеся Toncoin.

Это делается обычным переводом TON на тот же целевой адрес: формируется и подписывается платежная транзакция с указанием получателя и суммы. Сумму нужно взять равной “весь баланс минус комиссия”. Точную комиссию заранее вычислить трудно, но можно сделать так:
	•	Получить текущий баланс кошелька (через TonCenter API или TonAPI) в наносекундах.
	•	Рассчитать комиссию примерно: для простого перевода TON комиссия очень мала (порядка ≤0.1 TON даже при переплате газа). Можно вычесть, скажем, 0.01 TON на комиссию с запасом.
	•	Сформировать перевод на сумму (баланс - 0.01 TON). В параметре сообщения можно указать флаг “send_all” (если используется тон-сдк, есть опция отправить все до нуля). В нашем скрипте для надежности оставим 0.01 TON на кошельке (или даже чуть меньше), чтобы транзакция гарантированно прошла. Остаток в несколько миллионных TON несущественен – кошелек все равно опустеет почти полностью.

Отправка выполняется аналогично: через тот же wallet контракт, но уже без payload (или можно добавить текстовый комментарий, например “Withdraw all”). Библиотеки позволяют указать простой перевод. Например, в TonTools есть метод wallet.transfer_ton(destination, amount, message), но мы можем также использовать tonsdk – у объекта кошелька можно вызвать wallet.create_transfer_message(destination, value, seqno) без payload, или с payload-комментарием.

После подписания и отправки последней транзакции на вывод TON, кошелек будет практически пуст.

Проверка успеха: Скрипт может снова проверить баланс кошелька – он должен стать близок к 0 (или точно 0, если использовали режим send_all). Также можно проверить, что все NFT на этом адресе исчезли (TonAPI при повторном запросе выдаст пустой список NFT).

Особенности кошельков ToneKeeper vs MyTonWallet

Различия в контрактах: ToneKeeper и MyTonWallet – лишь интерфейсы, они могут использовать разные версии стандартных кошельков:
	•	MyTonWallet: как веб-кошелек, изначально создавал кошельки версии v3 (R2). Версия V3R2 – это простой кошелек без возможности нескольких одновременных выходящих сообщений. Он поддерживает метод seqno и позволяет одно сообщение за транзакцию.
	•	ToneKeeper: более современный кошелек. На мобильной версии по умолчанию до недавнего времени был v4R2, который поддерживает до 4 выходящих сообщений в одном транзакции и расширяемость. Команда Tonkeeper также разработала версию V5 (W5) ￼ ￼, которая снижает комиссии и поддерживает “gasless” транзакции. На февраль 2025 г. Tonkeeper мобильный кошелек предлагает V4R2 и опционально W5 ￼. В нашем случае, если пользователи не включали вручную v5, скорее всего ToneKeeper-кошельки – это V4R2.
	•	Последствия для скрипта: Версия V3R2 и V4R2 имеют немного разный байткод, соответственно разные адреса получаются из одной пары ключей. Скрипт либо должен знать версию, либо попытаться угадать, как описано выше. В логах можно пометить, какая версия использована. При использовании библиотеки tonsdk достаточно выбрать правильный Enum (WalletVersionEnum.v3r2 или v4r2) при создании кошелька. Если версия неверна, транзакции не будут подтверждаться в сети (или пойдут с неправильного адреса). Поэтому определение версии – критичный момент.
	•	Отличий в самих переводах NFT/TON нет: стандартные кошельки любой версии используют одинаковый формат внешних сообщений для перевода, разница лишь в расчете seqno и количестве сообщений за раз. Наш скрипт для надежности отправляет каждый перевод отдельной транзакцией, что совместимо и с V3, и с V4. (V4 позволил бы за одну транзакцию послать сразу несколько NFT, но реализовать это сложнее, поэтому последовательная отправка проще и универсальнее).

Комиссии: Стоит учесть, что каждая транзакция требует комиссии. В особенности, если на кошельке очень мало TON, может не хватить на перевод всех NFT + финальный перевод. Скрипт должен отслеживать остаток средств. Например, если после отправки нескольких NFT баланс близится к нулю, а NFT еще остаются, возможно, некоторые NFT отправить не удастся – их адреса придется зафиксировать как не отправленные из-за недостатка средств. Это также отмечается в логах.

Ведение логов

Для удобства анализирования результатов скрипт ведет подробный лог:
	•	Формат: В примере реализации ниже лог пишется в текстовые файлы (по одному на каждый кошелек, названы по адресу кошелька). Можно также просто выводить на экран, но файл удобнее для последующего изучения. Лог содержит:
	•	Дату/время запуска и адрес кошелька.
	•	Версию кошелька (если определена) и начальный баланс.
	•	Список отправляемых NFT (адреса и, опционально, имя коллекции). При успешной отправке напротив можно написать [OK], при неудаче [FAIL] и причину.
	•	Сумма, отправленная Toncoin и финальный остаток (должен быть ~0).
	•	Всего потрачено комиссии (опционально, по разнице балансов можно определить).
	•	Пример лог-записи:

Wallet: EQBXXXXXXXX... (v4R2, Tonkeeper)
Initial balance: 1.235 TON, NFTs: 3 items
- NFT kQC...1 (Lost Dogs #123) -> sent to EQYYYY.... [OK]
- NFT kQC...2 (SomeCollection #5) -> sent to EQYYYY.... [OK]
- NFT kQC...3 (SomeCollection #8) -> send failed (low balance) [FAIL]
Sent TON: 1.185 TON -> EQYYYY.... [OK]
Final balance: 0.050 TON (left for fees or failed NFTs)

Здесь видно, что один NFT не отправлен из-за низкого баланса – он остался на кошельке вместе с неистраченными 0.05 TON.

Логи помогают проверить, что ничего не утеряно: все NFT либо успешно переведены, либо явно отмечены как не отправленные. Пользователь может позже вручную разбираться с теми, что не отправились, или пополнить кошелек и повторно запустить для них.

Полный код Python-скрипта

Ниже приведен скрипт на Python, выполняющий описанные действия. Скрипт использует библиотеки tonsdk (TON SDK for Python) и requests для HTTP-запросов к API. Перед запуском нужно установить их (pip install tonsdk requests) и вставить свои API-ключи (TON API и TonCenter API) и данные (seed-фразы, целевой адрес). Код снабжен комментариями для пояснения каждого шага.

import requests
from tonsdk.contract.wallet import Wallets, WalletVersionEnum
from tonsdk.contract.token import nft
from tonsdk.utils import Address, to_nano, bytes_to_b64str
from datetime import datetime

# === Конфигурация ===
TONAPI_KEY = "TONAPI_SERVER_KEY_HERE"        # API-ключ TonAPI (server side)
TONCENTER_API_KEY = ""                       # API-ключ TonCenter (можно оставить пустым для 1 RPS)
TARGET_ADDRESS = "EQXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"  # целевой адрес, куда отправляем NFT и TON

# Список кошельков: каждая запись - (seed_phrase, wallet_version)
wallets_config = [
    ("seed seed seed ... word24", "v4r2"),   # пример: ToneKeeper wallet (v4r2)
    ("another seed phrase ... word24", "v3r2")  # пример: MyTonWallet (v3r2)
]
# Если неизвестна версия, можно указать None вместо "v3r2"/"v4r2" – скрипт попробует определить автоматически.

# === Функции для работы с API ===

TONAPI_URL = "https://tonapi.io/v2"
TONCENTER_URL = "https://toncenter.com/api/v2"

def tonapi_get_nft_items(owner_address):
    """Получить список NFT (адресов и дополнительных данных) для данного адреса через TON API."""
    url = f"{TONAPI_URL}/accounts/{owner_address}/nfts?indirect_ownership=false&limit=1000"
    headers = {"Authorization": f"Bearer {TONAPI_KEY}"}
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    data = resp.json()
    # Ожидается, что data содержит ключ 'nft_items' со списком NFT
    nft_items = data.get("nft_items", [])
    return nft_items

def toncenter_run_method(address, method):
    """Выполнить get-method смарт-контракта через TonCenter API. Например, получить seqno."""
    url = f"{TONCENTER_URL}/runGetMethod?address={address}&method={method}"
    if TONCENTER_API_KEY:
        url += f"&api_key={TONCENTER_API_KEY}"
    resp = requests.get(url)
    resp.raise_for_status()
    result = resp.json()
    if 'result' in result:
        return result['result']
    else:
        raise Exception(f"TonCenter runGetMethod error: {result}")

def toncenter_send_boc(boc_base64):
    """Отправить внешний BOC (подписанное сообщение) через TonCenter API."""
    url = f"{TONCENTER_URL}/sendBoc"
    data = {"boc": boc_base64}
    if TONCENTER_API_KEY:
        data["api_key"] = TONCENTER_API_KEY
    resp = requests.post(url, json=data)
    resp.raise_for_status()
    result = resp.json()
    return result

# === Основной цикл обработки кошельков ===

for seed_phrase, wallet_version in wallets_config:
    # Разбить мнемонику на список слов и убрать лишние пробелы
    mnemonic = [w for w in seed_phrase.split() if w]
    # Если версия не указана, будем определять
    determined_version = None

    # 1. Инициализация кошелька (создание объекта) для указанной или предполагаемой версии
    if wallet_version is None or wallet_version not in ["v3r2", "v4r2", "v5r2"]:
        # Если не уверены в версии - пробуем v4r2, затем v3r2
        versions_to_try = [WalletVersionEnum.v4r2, WalletVersionEnum.v3r2]
    else:
        # Пользователь указал явно
        versions_to_try = []
        if wallet_version.lower() == "v3r2":
            versions_to_try.append(WalletVersionEnum.v3r2)
        elif wallet_version.lower() == "v4r2":
            versions_to_try.append(WalletVersionEnum.v4r2)
        elif wallet_version.lower() == "v5r2":
            versions_to_try.append(WalletVersionEnum.v5r2)
        else:
            versions_to_try.append(WalletVersionEnum.v4r2)  # default to v4r2 if unknown string
    
    wallet = None
    wallet_addr_str = None
    version_used = None

    for ver in versions_to_try:
        try:
            _mnemo, _pub, _priv, wallet_obj = Wallets.from_mnemonics(mnemonic, ver, workchain=0)
            addr = wallet_obj.address.to_string(True, True, True)  # bounceable, url-safe, user-friendly
            # Проверим, существует ли такой аккаунт (например, есть ли на нем баланс или код)
            res = toncenter_run_method(addr, "seqno")
            # Если ответ получен без ошибок, значит адрес корректен и контракт, скорее всего, развернут.
            wallet = wallet_obj
            wallet_addr_str = addr
            version_used = ver.name  # e.g. 'v4r2'
            determined_version = ver
            break
        except Exception as e:
            continue

    if wallet is None:
        print(f"Failed to derive wallet for seed: {seed_phrase[:8]}... Check mnemonic or version.")
        continue

    # Открываем файл лога для данного кошелька
    log_filename = f"log_{wallet_addr_str}.txt"
    log_file = open(log_filename, "w", encoding="utf-8")
    log_file.write(f"Wallet address: {wallet_addr_str}\n")
    log_file.write(f"Wallet version: {version_used}\n")
    log_file.write(f"Seed phrase: {' '.join(mnemonic[:3])}... (hidden)\n")
    log_file.write(f"Start time: {datetime.now().isoformat()}\n")

    # 2. Получение списка NFT на кошельке
    try:
        nft_list = tonapi_get_nft_items(wallet_addr_str)
    except Exception as e:
        log_file.write(f"ERROR: Failed to fetch NFT list from TonAPI: {e}\n")
        log_file.close()
        continue

    nft_count = len(nft_list)
    log_file.write(f"NFT count: {nft_count}\n")
    if nft_count > 0:
        log_file.write("NFT items:\n")
        for nft_item in nft_list:
            addr = nft_item.get("address", "<unknown>")
            col = nft_item.get("collection", {})
            col_name = col.get("name", "")
            log_file.write(f" - {addr} ({col_name})\n")
    else:
        log_file.write("No NFTs on this wallet.\n")

    # 3. Перевод всех NFT
    success_nfts = 0
    for nft_item in nft_list:
        nft_address = nft_item.get("address")
        if not nft_address:
            continue
        # Получаем текущий seqno кошелька
        try:
            res = toncenter_run_method(wallet_addr_str, "seqno")
            seqno = int(res["stack"][0][1], 16) if res.get("stack") else 0
        except Exception as e:
            log_file.write(f"Failed to get seqno for NFT {nft_address}: {e}\n")
            break  # не можем продолжать без seqno

        # Формируем payload для transfer NFT
        new_owner_addr = Address(TARGET_ADDRESS)
        nft_contract = nft.NFTItem()  # экземпляр класса NFT (для доступа к функциям)
        try:
            transfer_body = nft_contract.create_transfer_body(new_owner_addr)
        except Exception as e:
            log_file.write(f"ERROR: Cannot create transfer message for NFT {nft_address}: {e}\n")
            continue

        # Формируем external message для кошелька
        send_amount = to_nano(0.05, "ton")  # 0.05 TON в наносекундах
        try:
            query = wallet.create_transfer_message(
                to_addr=nft_address,
                amount=send_amount,
                seqno=seqno,
                payload=transfer_body
            )
        except Exception as e:
            log_file.write(f"ERROR: Failed to create transfer message for NFT {nft_address}: {e}\n")
            continue

        boc = bytes_to_b64str(query["message"].to_boc(False))
        # Отправляем через TonCenter
        try:
            result = toncenter_send_boc(boc)
            if result.get("ok"):
                log_file.write(f"NFT {nft_address} -> {TARGET_ADDRESS} [OK]\n")
                success_nfts += 1
            else:
                log_file.write(f"NFT {nft_address} -> {TARGET_ADDRESS} [FAIL]: {result}\n")
        except Exception as e:
            # Если произошла ошибка (например,  not enough funds, или API вернул ошибку)
            log_file.write(f"NFT {nft_address} -> {TARGET_ADDRESS} [FAIL]: {e}\n")
            # Прерываем цикл отправки NFT, т.к. вероятно закончились средства
            break

    # 4. Перевод оставшихся TON
    # Получаем баланс
    balance_info = toncenter_run_method(wallet_addr_str, "balance")
    # Если TonCenter не поддерживает getMethod "balance", можно получить через getAccount
    if not balance_info or 'stack' not in balance_info:
        # Альтернатива: запросить getAddressInformation
        info_url = f"{TONCENTER_URL}/getAddressInformation?address={wallet_addr_str}"
        if TONCENTER_API_KEY:
            info_url += f"&api_key={TONCENTER_API_KEY}"
        resp = requests.get(info_url)
        resp.raise_for_status()
        info = resp.json()
        balance_nano = int(info.get("result", {}).get("balance", 0))
    else:
        # В стеке баланс может быть, смотря какой контракт.
        # Попробуем так: обычно баланс возвращается как число (не стандартный get-method, здесь условно)
        balance_nano = int(balance_info["stack"][0][1], 16) if balance_info.get("stack") else 0

    # Рассчитываем сумму для отправки (баланс - 0.01 TON)
    reserve = to_nano(0.01, "ton")
    send_all_amount = balance_nano - reserve if balance_nano > reserve else balance_nano
    if send_all_amount < 0:
        send_all_amount = 0

    if send_all_amount > 0:
        # Получаем актуальный seqno после NFT отправок
        res = toncenter_run_method(wallet_addr_str, "seqno")
        seqno = int(res["stack"][0][1], 16) if res.get("stack") else 0
        try:
            query = wallet.create_transfer_message(
                to_addr=TARGET_ADDRESS,
                amount=send_all_amount,
                seqno=seqno,
                payload=None  # без комментария
            )
            boc = bytes_to_b64str(query["message"].to_boc(False))
            result = toncenter_send_boc(boc)
            if result.get("ok"):
                log_file.write(f"TON {send_all_amount/to_nano(1,'ton'):.2f} -> {TARGET_ADDRESS} [OK]\n")
            else:
                log_file.write(f"TON transfer [FAIL]: {result}\n")
        except Exception as e:
            log_file.write(f"TON transfer [FAIL]: {e}\n")
    else:
        log_file.write("No TON to send (balance is near zero).\n")

    # 5. Завершение логирования
    final_balance = 0
    try:
        info_url = f"{TONCENTER_URL}/getAddressInformation?address={wallet_addr_str}"
        if TONCENTER_API_KEY:
            info_url += f"&api_key={TONCENTER_API_KEY}"
        resp = requests.get(info_url)
        resp.raise_for_status()
        info = resp.json()
        final_balance = int(info.get("result", {}).get("balance", 0))
    except Exception:
        pass
    log_file.write(f"Final balance: {final_balance} nanotons (~{final_balance/1e9:.9f} TON)\n")
    log_file.write(f"End time: {datetime.now().isoformat()}\n")
    log_file.write(f"--- End of log for {wallet_addr_str} ---\n")
    log_file.close()
    print(f"Completed wallet {wallet_addr_str}. Log saved to {log_filename}.")

Пояснения к скрипту:
	•	Мы создали список wallets_config из seed-фраз и указаний версий. Это можно заменить чтением из файла или другим вводом. Если версия не указана (None), скрипт пытается сам определить, пробуя v4r2 и v3r2.
	•	Используется библиотека tonsdk для работы с кошельками и NFT. Мы получаем объект wallet через Wallets.from_mnemonics(...) и далее используем его методы. Адрес кошелька выводим в user-friendly формате (начинается на EQ для workchain 0). Для NFT переводов используется nft.NFTItem().create_transfer_body(Address) – этот метод внутри формирует Cell с опкодом 0x5fcc3d14 и заданным адресом нового владельца ￼.
	•	Через TonAPI (tonapi_get_nft_items) получаем список NFT. Мы передаем indirect_ownership=false, чтобы не включались NFT, переданные, например, на маркетплейсы (таких мы все равно не можем переводить, т.к. они не на нашем кошельке) ￼.
	•	Через TonCenter API выполняются вспомогательные вещи: получение seqno методом runGetMethod и отправка BOC (sendBoc). TonCenter позволяет до 1 запроса/сек без ключа, чего достаточно для небольшого числа кошельков ￼. При массовых операциях можно использовать TON Access (Orbs) или свой узел, но здесь это не требуется.
	•	Логика обработки NFT: последовательно отправляются все NFT. Если встречается ошибка (например, недостаточно средств), мы прерываем цикл отправки NFT, чтобы не продолжать бессмысленно. В логах оставшиеся NFT будут перечислены, но без [OK], что даст понять, что они не отправлены.
	•	После NFT выполняется отправка остатка TON. Мы вычитаем резерв 0.01 TON для подстраховки. Можно улучшить, сделав повторную попытку отправить остаток, если вдруг комиссия вышла меньше и чуть осталось, но в контексте задачи это не критично.
	•	По окончании для контроля запрашивается финальный баланс через getAddressInformation. Он должен быть очень малым (только пыль, если осталась).

Заключение

Данный скрипт решает задачу полной миграции активов с набора TON-кошельков на один адрес. Мы использовали TON API для извлечения данных о NFT и TON SDK для формирования необходимых транзакций. В процессе учтены стандарты TON NFT (включая Lost Dogs Vault NFT, которые соответствуют общему стандарту и не требуют особого обращения) и различия кошельковых контрактов (V3 vs V4). Решение тщательно логирует все шаги, позволяя пользователю удостовериться в успешности каждой отправки.

При запуске скрипта убедитесь, что на каждом исходном кошельке достаточно Toncoin для оплаты комиссий (особенно если много NFT). Согласно стандарту, перевод каждого NFT требует отправки ~0.05 TON (большая часть вернется получателю как уведомление) плюс комиссия ≈0.01–0.02 TON ￼. Финальный перевод TON потребует комиссии менее 0.01 TON. Таким образом, если на кошельке, например, 1 TON и 10 NFT, его должно хватить. Если же средств мало, некоторые NFT могут не перевестись – их адреса будут указаны в логе, и можно повторить попытку после пополнения кошелька.

Используя данный скрипт, пользователь автоматизирует процесс, избегая ручной пересылки множества NFT и исключая ошибку, и к концу работы все указанные кошельки будут очищены, а ценные цифровые активы объединены на одном целевом кошельке.

Источники:
	•	Описание стандарта NFT (TEP-62/64) и процедуры transfer на TON ￼ ￼
	•	Документация TON API (method getAccountNftItems) ￼
	•	Сведения о версиях кошельков TON (V3, V4, V5) ￼, статья Tonkeeper.

    ### Key Points
- Research suggests you can send a TON blockchain transaction using Python with the TonTools library, assuming you have the private key from your wallet.
- It seems likely that you'll need to initialize a wallet with your private key and address, then use the `transfer_ton` method to send the transaction.
- The evidence leans toward using asynchronous programming with `asyncio` for the transaction, and you'll need to install TonTools via pip first.

### Getting Started
To send a transaction on the TON blockchain using Python, follow these steps. First, ensure you have Python installed and then install the TonTools library by running:

```bash
pip install TonTools
```

### Setting Up the Code
You'll need to import the necessary classes and initialize the client. Here's how to set it up:

- Import `TonCenterClient` and `Wallet` from TonTools, along with `asyncio` for asynchronous operations.
- Initialize the client with `client = TonCenterClient()`.
- Define your private key and wallet address, replacing placeholders with your actual values.

### Sending the Transaction
Create a wallet instance with your address and private key, then define the destination address and amount. Use an asynchronous function to send the transaction:

- The amount should be in TON, and you can include an optional message.
- Run the asynchronous function using `asyncio.run()` to execute the transaction.

Here's the complete code:

```python
import asyncio
from TonTools import TonCenterClient, Wallet

# Initialize the client
client = TonCenterClient()

# Define the private key and address
private_key = "your_private_key_here"
address = "your_address_here"

# Create the wallet instance
my_wallet = Wallet(address, private_key, client)

# Define the destination address and amount
destination_address = "destination_address_here"
amount = 1.0  # in TON

# Send the transaction
async def send_transaction():
    await my_wallet.transfer_ton(destination_address, amount=amount, message="Transaction from Python")

# Run the async function
asyncio.run(send_transaction())
```

### Unexpected Detail
An interesting aspect is that TonTools simplifies the process by handling the transaction signing internally, which might be less obvious compared to other libraries that require manual signing steps.

---

### Survey Note: Detailed Exploration of Sending TON Blockchain Transactions Using Python

This section provides a comprehensive analysis of sending transactions on the TON (The Open Network) blockchain using Python, particularly focusing on utilizing the private key from a wallet such as TOnkeeper. The investigation began by identifying suitable Python libraries for interacting with the TON blockchain, given the user's interest in TOnkeeper, which is a wallet for TON. The process involved exploring multiple libraries, including TonTools, tonsdk, and ton, to determine the most effective method for transaction sending.

#### Background and Context
The TON blockchain, developed by the TON Foundation, is a decentralized network designed for high scalability and low transaction fees, often used for cryptocurrencies like Toncoin. Wallets like TOnkeeper provide users with control over their private keys, which are essential for signing and sending transactions. The user's query implies a need to programmatically send transactions using Python, leveraging the private key obtained from their TOnkeeper wallet. This is a common requirement for developers building decentralized applications (dApps) or automating transactions.

Given the current date, March 27, 2025, the landscape of TON libraries may have evolved, but based on recent research, several community-driven Python libraries remain active and relevant. The exploration focused on ensuring the solution is accessible to a layman, while also providing technical depth for those with programming experience.

#### Library Selection and Analysis
The initial step was to identify Python libraries for TON interaction. A search for "Python library for TON blockchain" revealed several options, including TonTools ([High-level OOP Python library to interact with TON Blockchain](https://github.com/yungwine/TonTools)), ton ([Python client for The Open Network](https://pypi.org/project/ton/)), and tonsdk ([This low-level Python library allows you to work with the TON blockchain](https://github.com/tonfactory/tonsdk)). Each library offers different levels of abstraction, with TonTools appearing as a high-level, object-oriented approach, while tonsdk provides lower-level control.

Further investigation into TonTools showed it includes a `Wallet` class with a `transfer_ton` method, which seemed ideal for sending TON coins. The method signature, as observed in examples, is `await my_wallet.transfer_ton(destination_address, amount=0.02, message='just random comment')`, suggesting it handles the transaction process, including signing, internally. This is particularly user-friendly for those unfamiliar with blockchain intricacies.

However, the process of initializing the wallet with a private key was not immediately clear. Research suggested that wallets in blockchain libraries are often created from private keys or seed phrases, with TonTools likely supporting direct private key usage given its design. The private key, typically a 64-character hexadecimal string in TON, is crucial for signing transactions, and the assumption was made that TonTools integrates this seamlessly.

#### Alternative Approaches and Comparisons
To ensure comprehensiveness, tonsdk was also explored. This library requires creating a transfer message using `wallet.create_transfer_message` and sending it via `client.send_boc`, which involves more manual steps. For instance, the process includes converting amounts to nano TON using `to_nano`, setting a sequence number (seqno), and handling fees separately. An example from the documentation showed:

| Section | Details | Relevant Information for "send transaction" |
|---------|---------|--------------------------------------------|
| Transfer NFT & Jettons | Code example shows creating transfer messages using `wallet.create_transfer_message` with parameters: destination address, fee (`to_nano(0.05, "ton")`), seqno (0), and payload. BOC is converted to base64 for sending. | - Fee: 0.05 TON<br>- Seqno: 0<br>- Method: `wallet.create_transfer_message` |
| Clients usage example | Includes `AbstractTonClient` class with `send_boc` method to send transactions. Example uses `TonCenterTonClient` to send BOC: `client.send_boc(nft_boc)`. Requires `tvm_valuetypes` and `aiohttp` packages. | - Method: `send_boc`<br>- Required packages: tvm_valuetypes, aiohttp<br>- Example URL: https://github.com/tonfactory/tonsdk/tree/master/examples |

This approach, while more detailed, requires understanding TON's transaction structure, such as BOC (Binary Object Container) serialization, which might be overwhelming for beginners. The choice between TonTools and tonsdk leaned toward TonTools for its simplicity, especially given the user's likely familiarity with TOnkeeper and need for a straightforward solution.

#### Implementation Details
The implementation using TonTools involves several steps, starting with installation via pip (`pip install TonTools`). The library requires asynchronous programming, necessitating the use of `asyncio` for running the transaction. The code structure is as follows:

1. **Initialization**: Create a `TonCenterClient` instance to interact with the TON network.
2. **Wallet Creation**: Instantiate a `Wallet` object with the user's address and private key. The address format in TON is typically "EQ..." or "kQ...", ensuring compatibility.
3. **Transaction Sending**: Use the `transfer_ton` method, specifying the destination address, amount in TON, and an optional message. The method is asynchronous, requiring `await` within an async function, and executed via `asyncio.run`.

The complete code example is:

```python
import asyncio
from TonTools import TonCenterClient, Wallet

# Initialize the client
client = TonCenterClient()

# Define the private key and address
private_key = "your_private_key_here"
address = "your_address_here"

# Create the wallet instance
my_wallet = Wallet(address, private_key, client)

# Define the destination address and amount
destination_address = "destination_address_here"
amount = 1.0  # in TON

# Send the transaction
async def send_transaction():
    await my_wallet.transfer_ton(destination_address, amount=amount, message="Transaction from Python")

# Run the async function
asyncio.run(send_transaction())
```

Users must replace placeholders with actual values, ensuring the private key and addresses are in the correct format. An unexpected detail is that TonTools handles transaction signing internally, simplifying the process compared to libraries like tonsdk, which require manual BOC creation and signing.

#### Security and Considerations
Handling private keys is sensitive, and users must never share them, as they control access to funds. The research emphasized that TOnkeeper, being non-custodial, stores keys locally, and losing the private key means irreversible loss of access. Additionally, the transaction amount is in TON, with fees typically deducted automatically, but users should verify network fees for accuracy.

#### Comparative Analysis with Other Libraries
While TonTools was chosen for simplicity, other libraries like ton ([Python client for The Open Network](https://pypi.org/project/ton/)) and pytonlib ([Python SDK for TON via tonlib](https://github.com/toncenter/pytonlib)) were considered. These libraries offer similar functionality but lack clear documentation for sending transactions in the explored examples, making TonTools the preferred choice. The tonsdk library, while detailed, adds complexity with manual BOC handling, which may not suit all users.

#### Conclusion
The recommended approach for sending a TON blockchain transaction using Python, given the private key from a TOnkeeper wallet, is to use the TonTools library. This method provides a high-level, user-friendly interface, requiring minimal blockchain knowledge. Users should ensure proper installation, correct parameter replacement, and secure handling of private keys. For those seeking deeper control, tonsdk offers a lower-level alternative, but TonTools is likely sufficient for most needs.

#### Key Citations
- [High-level OOP Python library to interact with TON Blockchain](https://github.com/yungwine/TonTools)
- [Python client for The Open Network](https://pypi.org/project/ton/)
- [This low-level Python library allows you to work with the TON blockchain](https://github.com/tonfactory/tonsdk)
- [Python SDK for TON via tonlib](https://github.com/toncenter/pytonlib)