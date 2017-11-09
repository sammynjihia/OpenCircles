import datetime
from wallet.models import RevenueStreams


class RevenueStreamsUtils:

    @staticmethod
    def get_revenue_streams_by_date(search_date=None):
        if search_date is None:
            search_date = datetime.datetime.now()
        revenue_streams = RevenueStreams.objects.filter(
            time_of_transaction__range=(
                datetime.datetime.combine(search_date, datetime.time.min),
                datetime.datetime.combine(search_date, datetime.time.max)))
        return revenue_streams

    @staticmethod
    def get_revenue_by_date(start_date=None, end_date=None):
        revenue_stream = None
        print(start_date)
        print(end_date)
        if start_date is None and end_date is None:
            revenue_stream = RevenueStreams.objects.filter(time_of_transaction__range=(
                datetime.datetime.combine(datetime.date.today(), datetime.time.min),
                datetime.datetime.combine(datetime.datetime.today(), datetime.time.max)))

        if start_date is not None and end_date is None:
            revenue_stream = RevenueStreams.objects.filter(time_of_transaction__gte=start_date)

        if start_date is None and end_date is not None:
            revenue_stream = RevenueStreams.objects.filter(time_of_transaction__lte=end_date)

        if start_date is not None and end_date is not None:
            revenue_stream = RevenueStreams.objects.filter(time_of_transaction__range=(
                datetime.datetime.combine(start_date, datetime.time.min),
                datetime.datetime.combine(end_date, datetime.time.max)))
        revenue_stream = revenue_stream.order_by('time_of_transaction')
        return revenue_stream









