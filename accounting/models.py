from django.db import models
from django.contrib.auth.models import User

class Organization(models.Model):
    """Организация.

    МУП - это частный случай организации, поэтому МУП находится в этой модели.
    """
    name = models.CharField(max_length=200)
    def __str__(self):
        return self.name

class UserOrganization(models.Model):
    """Связь пользователь-организация.

    Пользователи бывают администраторами, клиентами организации, работниками
    организации. Связь показывает какой именно пользователь сайта является
    работником организации.
    """
    user = models.ForeignKey(User)
    organization = models.ForeignKey(Organization, null=True, blank=True, default = None)

class RealEstate(models.Model):
    """Объект недвижимости.

    Объектом недвижимости может являться многоквартирный дом, жилой дом,
    квартира, комната. При этом у модели есть связь, которая показывает,
    например, какая именно комната принадлежит какой именно квартире.

    cold_water_counter_setup_date -- это дата установки счетчика холодной
    воды. Не совсем понятна ситуация со сменой счетчиков, т.е. должна ли
    находится информация cold_water_counter_setup_date именно в объекте
    недвижимости.
    """
    address = models.CharField(max_length=200)
    parent = models.ForeignKey('self', null=True, blank=True, default = None)
    cold_water_counter_setup_date = models.DateField(blank=True, null=True)
    def __str__(self):
        return self.address

class Client(models.Model):
    """Клиент.

    Клиент принадлежит организации, которая предоставляет ему услуги.
    У клиента есть свой лицевой счет, который характеризуется его номером,
    сейчас это ID клиента, и суммой на лицевом счете. Лицевой счет
    инкапсулирован в понятие клиента.
    TODO: со временем перенести поля residential residents в отдельную
    таблицу, потому что эта информация может меняться, а иногда полезно делать
    перерасчет, но информация, возможна будет потеряна.
    residential -- флаг, указывающий жилое ли помещение. Находится здесь,
    потому что как используется помещение зависит больше от клиента, а не от
    помещения.
    """
    lfm = models.CharField(max_length=200)
    organization = models.ForeignKey(Organization)
    amount = models.DecimalField(max_digits=8, decimal_places=2, default=1)
    real_estate = models.ForeignKey(RealEstate)
    residential = models.BooleanField(default=True)
    residents = models.IntegerField(default=-1)
    def __str__(self):
        return self.lfm + "(" + self.organization.__str__() + ")"

class Payment(models.Model):
    """Платеж.

    Платеж увеличивает сумму на лицевом счете клиента.
    TODO: Текущая модель рабочая, но не актуальная.
    """
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    client = models.ForeignKey(Client)
    real_estate = models.ForeignKey(RealEstate, null=True, blank=True, default = None)

class ServiceClient(models.Model):
    """Связь услуга-клиент.

    Связь указывает на то, какая именно услуга потребляется определенным
    клиентом. Альтернатива выставить флаг в модели Client, но тогда не сможем
    отключать услугу, выставлять ее время.
    """
    client = models.ForeignKey(Client)
    service_name = models.CharField(max_length=200)

class ColdWaterCounter(models.Model):
    """Показания приборов учета холодной воды."""
    value = models.IntegerField()
    real_estate = models.ForeignKey(RealEstate)
    date = models.DateField()
    def __str__(self):
        return str(self.date)

class ColdWaterValue(models.Model):
    """Вычисления объема потребления холодной воды."""
    value = models.IntegerField()
    real_estate = models.ForeignKey(RealEstate)
    date = models.DateField()
    def __str__(self):
        return str(self.date)

class ColdWaterTariff(models.Model):
    """Тариф по услуге холодного водоснабжения для конкретного клиента."""
    client = models.ForeignKey(Client)
    value = models.IntegerField()
    def __str__(self):
        return "%s %s" % (str(self.client), self.value)

