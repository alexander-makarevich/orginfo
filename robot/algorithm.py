from accounting.models import ColdWaterReading, ColdWaterVolume, RealEstate, Period, ServiceClient, Animals
import datetime
from django.db.models import Sum


def write_of_cold_water_service(client):
    """Списание средств за холодную воду.

    В ColdWaterReading за один отчетный период хранится только одно показание.
    Как быть в случае, когда установлен счетчик с ненулевым показанием? Ведь
    тогда откуда брать показание, оно будет явно описано в данных, а не будет
    хардкода в алгоритме.
    """
    use_norms = False

    periods_with_counter = None
    setup_date = client.real_estate.cold_water_counter_setup_date
    if setup_date:
        periods_with_counter = Period.objects.order_by('start').filter(start__gte=setup_date)

    if periods_with_counter and periods_with_counter.count() >= 6:
        last_period_reading = periods_with_counter.last().coldwaterreading_set.filter(real_estate=client.real_estate).get()
        was_reading_in_last_period = last_period_reading is not None
        if was_reading_in_last_period:
            #TODO: next_to_last_period_reading может отсутствовать.
            i = periods_with_counter.count() - 2
            while 0 <= i:
                readings = periods_with_counter[i].coldwaterreading_set.filter(real_estate=client.real_estate)
                if readings.count():
                    next_to_last_period_reading = readings.get()
                    break
                i = i - 1
            unconfirmed_reading_volumes = ColdWaterVolume.objects.filter(real_estate=client.real_estate, period__serial_number__in=range(last_period_reading.period.serial_number+1, next_to_last_period_reading.period.serial_number)).aggregate(Sum('volume'))['volume__sum'] or 0
            volume = last_period_reading.value - next_to_last_period_reading.value - unconfirmed_reading_volumes
            volume_model = ColdWaterVolume(period=periods_with_counter[periods_with_counter.count()-1], real_estate=client.real_estate, volume=volume, date=datetime.date.today())
            volume_model.save()

        second_from_the_end_period_reading = ColdWaterReading.objects.filter(real_estate=client.real_estate, period=periods_with_counter[periods_with_counter.count()-2]).last()
        third_from_the_end_period_reading = ColdWaterReading.objects.filter(real_estate=client.real_estate, period=periods_with_counter[periods_with_counter.count()-3]).last()
        was_reading_in_second_or_third_period_from_the_end = second_from_the_end_period_reading or third_from_the_end_period_reading
        if was_reading_in_second_or_third_period_from_the_end and was_reading_in_last_period == False:
            last_six_volumes_sum = ColdWaterVolume.objects.filter(real_estate=client.real_estate, period__serial_number__in=range(periods_with_counter.last().serial_number-6+1, periods_with_counter.last().serial_number+1)).aggregate(Sum('volume'))['volume__sum']
            average_volume = last_six_volumes_sum/6
            cold_water_volume = ColdWaterVolume(real_estate=client.real_estate, volume=average_volume, date=datetime.date.today())
            cold_water_volume.save()

        else:
            use_norms = True
    else:
        use_norms = True

    if use_norms and client.residential:
        #Формула № 4а
        volume = client.residents * client.type_water_norm.cold_water_norm
        cold_water_volume = ColdWaterVolume(real_estate=client.real_estate, volume=volume, date=datetime.date.today())
        cold_water_volume.save()
        pass
    else:
        #average_six_period_volume = 
        periods = Period.objects.order_by('start')
        start_period_index = periods.count()-6-1
        if start_period_index > 0:
            last_six_volumes_sum = ColdWaterVolume.objects.filter(real_estate=client.real_estate, period__serial_number__gte=periods[start_period_index].serial_number).aggregate(Sum('volume'))['volume__sum']
            average_volume = last_six_volumes_sum/6
            cold_water_volume = ColdWaterVolume(real_estate=client.real_estate, volume=average_volume, date=datetime.date.today())
            cold_water_volume.save()
        else:
            #TODO: нужен флаг -- manual
            pass

def write_off():
    """Списание средств с клиентских счетов.

    Списание произодится раз в месяц 25 числа.
    """
    for building in RealEstate.objects.filter(type=RealEstate.BUILDING_TYPE):
        periods = Period.objects.order_by('start')
        #TODO: счетчик может отсутствовать
        last_period_reading = periods[periods.count()-1].coldwaterreading_set.filter(real_estate=building).get()
        next_to_last_period_reading = periods[periods.count()-2].coldwaterreading_set.filter(real_estate=building).get()
        cold_water_building_volume = last_period_reading.value - next_to_last_period_reading.value

        real_estates = []
        for flat in RealEstate.objects.filter(parent=building):
            if flat.type == 'r':
                for room in RealEstate.objects.filter(parent=flat):
                    real_estates.append(room)
            else:
                real_estates.append(flat)

        #TODO: удобно определить cold_water_volume_clients_sum
        cold_water_volume_clients_sum = 800
        for real_estate in real_estates:
            client = real_estate.client_set.last()
            #TODO: как вычислить is_cold_water_service с учетом start/end 
            is_cold_water_service = client.serviceclient_set.filter(
                service_name=ServiceClient.COLD_WATER_SERVICE).last()
            if is_cold_water_service:
                write_of_cold_water_service(client)

        #расчет общедомовых нужд
        volume = (cold_water_building_volume - cold_water_volume_clients_sum) / len(real_estates)
        if volume != 0:
            for real_estate in real_estates:
                cold_water_volume = ColdWaterVolume(real_estate=real_estate, volume=volume, date=datetime.date.today())
                cold_water_volume.save()

        #TODO: списать средства с лицевого счета.

    for house in RealEstate.objects.filter(type=RealEstate.HOUSE_TYPE):
        client = house.client
        does_cold_water_counter_exist = False
        if does_cold_water_counter_exist:
            write_of_cold_water_service(client)
        else:
            volume = client.residents * client.type_water_norm.cold_water_norm
            cold_water_volume = ColdWaterVolume(real_estate=client.real_estate, volume=volume, date=datetime.date.today())
            cold_water_volume.save()
            
            #TODo: Вычислить объем для земельного участка и расположенных на нем надворных построек
            # У клиента могут быть виды сельскохозяйственных животных, направления использования
            # Вычисляем общий оъбем для видов сельскохозяйственных животных
            animals_volume = 0
            animals_for_house = Animals.objects.filter(real_estate=house)
            for animals in animals_for_house:
                animals_volume = animals_volume + (animals.count * animals.type.norm)
            
            # Вычисляем общий оъбем для направления использования
            use_case_volume = 0
                
            total_volume = animals_volume + use_case_volume
            period = Period.objects.last()
            cold_water_volume = ColdWaterVolume(period=period, real_estate=house, volume=total_volume, date=datetime.date.today())
            cold_water_volume.save()
            
            #TODO: списать средства с лицевого счета.
