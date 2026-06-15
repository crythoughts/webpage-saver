from yarl import URL
import json
from collections import defaultdict
from datetime import datetime, timedelta
import calendar

def toURLWithoutMeaninglessDiffs(url: str):
    u = URL(url)
    new_host = u.host

    if u.host.startswith('www.'):
        new_host = u.host[4:]

    return u.with_host(new_host).with_scheme('').human_repr()[2:]

def _groupRecordByDate(records, conv: bool = False):
    calendar_data = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

    for record in records:
        if record.taken_at == None:
            continue

        dt = datetime.fromtimestamp(record.taken_at)
        data = None
        if conv == True:
            data = record.toModel().dump()
        else:
            data = record.toModel()

        calendar_data[dt.year][dt.month][dt.day].append(data)

    return calendar_data

def _getCalendarStructure(year, month, records_dict: list):
    days_in_month = calendar.monthrange(year, month)[1]
    first_weekday = calendar.monthrange(year, month)[0]
    
    month_structure = {
        'year': year,
        'month': month,
        'month_name': calendar.month_name[month],
        'days_in_month': days_in_month,
        'first_weekday': first_weekday,
        'is_leap_year': calendar.isleap(year),
        'days': {}
    }

    for day in range(1, days_in_month + 1):
        date_key = datetime(year, month, day)
        day_records = records_dict.get(year, {}).get(month, {}).get(day, [])
        length = len(day_records)
        month_structure['days'][day] = {
            'date': date_key.strftime('%Y-%m-%d'),
            'weekday': calendar.day_name[date_key.weekday()],
            'records': day_records,
            'records_count': length,
            'has_records': length > 0
        }
    
    return month_structure

def getCalendarForPages(records, conv: bool = False):
    grouped_records = _groupRecordByDate(records, conv = conv)

    calendar_structure = {
        'years': {},
        'total_years': 0,
        'total_records': len(records) if hasattr(records, '__len__') else 0
    }
    if grouped_records:
        available_years = sorted(grouped_records.keys())
        min_year = available_years[0]
        max_year = available_years[-1]
    else:
        min_year = datetime.now().year
        max_year = datetime.now().year

    for year in range(min_year, max_year + 1):
        year_data = {
            'year': year,
            'is_leap_year': calendar.isleap(year),
            'months': {},
            'total_records_in_year': 0
        }
        
        for month in range(1, 13):
            month_structure = _getCalendarStructure(year, month, grouped_records)

            month_records_count = sum(
                len(day_data['records']) 
                for day_data in month_structure['days'].values()
            )

            month_structure['total_records'] = month_records_count
            year_data['months'][month] = month_structure
            year_data['total_records_in_year'] += month_records_count
        
        calendar_structure['years'][year] = year_data
    
    calendar_structure['total_years'] = len(calendar_structure['years'])
    
    return calendar_structure
