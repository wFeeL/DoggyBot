from typing import Tuple

def inflect_with_num(
    number: int, forms: Tuple[str, str, str]
) -> str:
    """В русском языке есть особенность, что идущее перед словом число
    может его в корни изменить.
    Например: 1 год, 2 года, 3 года, 4 года, 5 лет. Формы у групп 1,
    2-4, 5-10 отличается. В промежутке с 10 до 20 будут идти именно «лета».
    А после результат будет зависеть от цифры в разряде единиц.
    И так повторяется с каждой сотней.
    Для удобства восприятия назовём группы цифрами:
        1. Для единицы (1).
        2. Единица 0, от 5 до 9 и от 10 до 20 включительно.
        3. Единицы от 2 до 4 включительно.
    Массив forms принимает формы в том же порядке.
    :param number: Число, предшествующее слову
    :param forms: Три заданные формы исчисляемого слова
    :return:
    """

    units = number % 10
    tens = number % 100 - units
    if tens == 10 or units >= 5 or units == 0:
        needed_form = 1
    elif units > 1:
        needed_form = 2
    else:
        needed_form = 0
    return forms[needed_form]