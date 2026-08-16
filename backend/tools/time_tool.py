from datetime import datetime
import pytz


def get_time(timezone_name):
    try:
        timezone = pytz.timezone(timezone_name)
        current_time = datetime.now(timezone)

        return {
            "timezone": timezone_name,
            "time": current_time.strftime("%I:%M %p"),
            "date": current_time.strftime("%d %B %Y")
        }

    except pytz.UnknownTimeZoneError:
        return {
            "error": f"Unknown timezone: {timezone_name}"
        }

    except Exception as e:
        return {
            "error": str(e)
        }