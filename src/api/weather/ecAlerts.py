import asyncio
import datetime
import logging

debug = logging.getLogger("scoreboard")

class ecWxAlerts(object):
    def __init__(self, data, scheduler,sleepEvent):

        self.data = data
        self.time_format = data.config.time_format
        self.alert_frequency = data.config.wxalert_update_freq
        self.weather_alert = 0
        # Date format Friday April 03, 2020 at 04:36 CDT
        # Strip off the last 4 caharacters in the date string to remove timezone
        self.alert_date_format = "%A %B %d, %Y at %H:%M"
        self.network_issues = data.network_issues

        self.sleepEvent = sleepEvent
        self.sleepEvent.clear()

        scheduler.add_job(self.getAlerts, 'interval', minutes=self.alert_frequency,jitter=90,id='ecAlerts')
        #Check every 5 mins for testing only
        #scheduler.add_job(self.CheckForUpdate, 'cron', minute='*/5')

        #Get initial Alerts
        self.getAlerts()

    def getAlerts(self):
        debug.info("Checking for EC weather alerts")
        asyncio.run(self.data.ecData.update())
        curr_alerts = self.data.ecData.alerts
        self.network_issues = False

        debug.info("Last Alert: {0}".format(self.data.wx_alerts))
        debug.debug(curr_alerts)

        # --- Define RGB Colors ---
        # Format: (Red, Green, Blue)
        rgb_red = (255, 0, 0)
        rgb_orange = (255, 128, 0)
        rgb_yellow = (255, 255, 0)
        rgb_gray = (128, 128, 128)

        # Collect potential alerts
        found_alerts = []
        source_keys = ['warnings', 'watches', 'advisories']

        for key in source_keys:
            items = curr_alerts.get(key, {}).get("value", [])

            if len(items) > 0:
                item = items[0]
                raw_title = item.get("title", "")
                raw_date = item.get("date", "")[:-4]
                raw_expiry = item.get("expiryTime", "")


                # --- 1. DEFAULT VALUES (Legacy Fallback) ---
                # Default mapping if no color is found in the string
                if 'alertColourLevel' in item:
                    if item['alertColourLevel'] == "red":
                        color = rgb_red
                    elif item['alertColourLevel'] == "orange":
                        color = rgb_orange
                    elif item['alertColourLevel'] == "yellow":
                        color = rgb_yellow
                    else:
                        color = rgb_gray
                else:
                    if key == 'warnings':
                        category = "warning"
                        color = rgb_red
                    elif key == 'watches':
                        category = "watch"
                        color = rgb_orange
                    elif key == 'advisories':
                        category = "advisory"
                        color = rgb_yellow

                clean_title = raw_title

                # --- 2. PARSING LOGIC ---
                lower_title = raw_title.lower()

                # CHECK FOR NEW FORMAT: "Color Category - Description"
                if " - " in raw_title and any(c in lower_title for c in ['red', 'orange', 'yellow']):
                    parts = raw_title.split(" - ", 1)
                    header_part = parts[0].lower()
                    description_part = parts[1]

                    # Extract Color and assign RGB Tuple
                    if 'alertColourLevel' not in item:
                        if "red" in header_part:
                            color = rgb_red
                        elif "orange" in header_part:
                            color = rgb_orange
                        elif "yellow" in header_part:
                            color = rgb_yellow

                    # Extract Category
                    if "warning" in header_part:
                        category = "warning"
                    elif "watch" in header_part:
                        category = "watch"
                    elif "advisory" in header_part:
                        category = "advisory"

                    clean_title = description_part

                # CHECK FOR LEGACY SUFFIXES
                else:
                    if lower_title.endswith(" warning"):
                        clean_title = raw_title[:-(len(" Warning"))]
                        category = "warning"
                        if 'alertColourLevel' not in item:
                            color = rgb_red
                    elif lower_title.endswith(" watch"):
                        clean_title = raw_title[:-(len(" Watch"))]
                        category = "watch"
                        if 'alertColourLevel' not in item:
                            color = rgb_orange
                    elif lower_title.endswith(" advisory"):
                        clean_title = raw_title[:-(len(" Advisory"))]
                        category = "advisory"
                        if 'alertColourLevel' not in item:
                            color = rgb_yellow

                # --- 3. TIME FORMATTING ---
                try:
                    alert_datetime = datetime.datetime.strptime(raw_date, self.alert_date_format)
                    if self.time_format == "%H:%M":
                        formatted_time = alert_datetime.strftime("%m/%d %H:%M")
                    else:
                        formatted_time = alert_datetime.strftime("%m/%d %I:%M %p")
                except ValueError:
                    formatted_time = raw_date

                if raw_expiry:
                    try:
                        expiry_datetime = datetime.datetime.strptime(raw_expiry, '%Y%m%d%H%M%S')
                        if self.time_format == "%H:%M":
                            formatted_expiry = expiry_datetime.strftime("%m/%d %H:%M")
                        else:
                            formatted_expiry = expiry_datetime.strftime("%m/%d %I:%M %p")
                    except ValueError:
                        formatted_expiry = raw_expiry
                else:
                    formatted_expiry = ""


                # --- 4. ADD TO LIST ---
                # Structure: [Title, Category, Time, RGB Tuple]
                found_alerts.append([clean_title, category, formatted_time, color, formatted_expiry])

        # --- PROCESS RESULTS ---
        num_alerts = len(found_alerts)

        if num_alerts > 0:
            found_alerts.sort(key=lambda x: x[2], reverse=True)
            current_alert = found_alerts[0]

            # Shorten common long titles
            if current_alert[0] == "Severe Thunderstorm":
                current_alert[0] = "Svr T-Storm"
            if current_alert[0] == "Freezing Rain":
                current_alert[0] = "Frzn Rain"
            if current_alert[0] == "Freezing Drizzle":
                current_alert[0] = "Frzn Drzl"

            if self.data.wx_alerts != current_alert:
                self.data.wx_alerts = current_alert
                self.weather_alert = 0
                debug.info("Current Alert: {0}".format(self.data.wx_alerts))

            wx_num_endings = len(curr_alerts.get("endings", {}).get("value", []))
            if wx_num_endings > 0:
                ending_item = curr_alerts["endings"]["value"][0]
                ending_date = ending_item["date"][:-4]
                try:
                    end_dt = datetime.datetime.strptime(ending_date, self.alert_date_format)
                    if self.time_format == "%H:%M":
                        end_time = end_dt.strftime("%m/%d %H:%M")
                    else:
                        end_time = end_dt.strftime("%m/%d %I:%M %p")
                except:
                    end_time = ending_date

                # Endings: use Gray RGB
                endings = [ending_item["title"], "ended", end_time, rgb_gray]

                self.data.wx_alert_interrupt = False
                self.weather_alert = 0
                self.data.wx_alerts = []
                debug.info(endings)

            if wx_num_endings == 0:
                if self.weather_alert == 0:
                    self.data.wx_alert_interrupt = True
                    self.sleepEvent.set()
                self.weather_alert += 1

        else:
            debug.info("No active EC weather alerts in your area")
            self.data.wx_alert_interrupt = False
            self.data.wx_alerts.clear()
            self.weather_alert = 0
