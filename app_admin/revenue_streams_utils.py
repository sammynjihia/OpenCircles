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








