import os
import threading
import requests
from datetime import datetime, timedelta, timezone

from flask import Flask, request, jsonify
from slack_sdk import WebClient
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler


# ============================================================
# FLASK APP
# ============================================================

app = Flask(__name__)


# ============================================================
# SLACK CLIENT
# ============================================================

slack = WebClient(
    token=os.environ.get("SLACK_BOT_TOKEN")
)


bolt_app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET")
)


# ============================================================
# CONFIGURATION
# ============================================================

WARNING_CHANNEL = "#warning-alerts"
CRITICAL_CHANNEL = "#critical-alters"

ALERTMANAGER_URL = os.environ.get(
    "ALERTMANAGER_URL",
    "http://127.0.0.1:9093"
)


# ============================================================
# BUILD SLACK ALERT MESSAGE
# ============================================================

def build_alert_message(alert, status):

    labels = alert.get("labels", {})
    annotations = alert.get("annotations", {})

    alertname = labels.get(
        "alertname",
        "Unknown"
    )

    severity = labels.get(
        "severity",
        "unknown"
    ).upper()

    instance = labels.get(
        "instance",
        "Unknown"
    )

    summary = annotations.get(
        "summary",
        ""
    )

    description = annotations.get(
        "description",
        ""
    )

    starts_at = alert.get(
        "startsAt",
        ""
    )


    # --------------------------------------------------------
    # FIRING
    # --------------------------------------------------------

    if status == "firing":

        title = "🚨 ALERT FIRING — Production Monitoring"

        status_text = "🔴 FIRING"


    # --------------------------------------------------------
    # RESOLVED
    # --------------------------------------------------------

    else:

        title = "✅ ALERT RESOLVED — Production Monitoring"

        status_text = "🟢 RESOLVED"


    # --------------------------------------------------------
    # TEXT
    # --------------------------------------------------------

    text = (
        f"*{title}*\n\n"

        f"*Alert:* {alertname}\n"

        f"*Severity:* {severity}\n"

        f"*Server:* {instance}\n\n"

        f"*Summary:* {summary}\n\n"

        f"*Description:*\n"
        f"{description}\n\n"

        f"*Started:* {starts_at}\n\n"

        f"*Status:* {status_text}"
    )


    # --------------------------------------------------------
    # BLOCKS
    # --------------------------------------------------------

    blocks = [

        {
            "type": "section",

            "text": {
                "type": "mrkdwn",
                "text": text
            }
        }

    ]


    # --------------------------------------------------------
    # BUTTONS FOR FIRING ALERTS
    # --------------------------------------------------------

    if status == "firing":

        blocks.append(

            {
                "type": "actions",

                "elements": [

                    {
                        "type": "button",

                        "text": {
                            "type": "plain_text",
                            "text": "ACCEPT"
                        },

                        "style": "primary",

                        "action_id": "accept_alert",

                        "value": alert.get(
                            "fingerprint",
                            ""
                        )
                    },


                    {
                        "type": "button",

                        "text": {
                            "type": "plain_text",
                            "text": "REJECT"
                        },

                        "style": "danger",

                        "action_id": "reject_alert",

                        "value": alert.get(
                            "fingerprint",
                            ""
                        )
                    }

                ]
            }

        )


    return text, blocks


# ============================================================
# CREATE ALERTMANAGER SILENCE
# ============================================================

def create_alertmanager_silence(labels, user_name):

    """
    Create a 4-hour Alertmanager silence.

    The silence matches ALL labels of the specific alert.
    This prevents accidentally silencing alerts from another
    server that have the same alertname.
    """

    matchers = []


    # --------------------------------------------------------
    # CREATE MATCHERS FROM ALERT LABELS
    # --------------------------------------------------------

    for name, value in labels.items():

        matchers.append(

            {
                "name": name,
                "value": value,
                "isRegex": False
            }

        )


    # --------------------------------------------------------
    # SILENCE TIME
    # --------------------------------------------------------

    starts_at = datetime.now(
        timezone.utc
    )

    ends_at = starts_at + timedelta(
        hours=4
    )


    # --------------------------------------------------------
    # SILENCE PAYLOAD
    # --------------------------------------------------------

    silence = {

        "matchers": matchers,

        "startsAt": starts_at.isoformat(),

        "endsAt": ends_at.isoformat(),

        "createdBy": user_name,

        "comment":
            f"Alert acknowledged by {user_name} via Slack"

    }


    print(
        "Creating Alertmanager silence..."
    )

    print(
        f"Silence starts: {starts_at.isoformat()}"
    )

    print(
        f"Silence ends: {ends_at.isoformat()}"
    )


    # --------------------------------------------------------
    # SEND TO ALERTMANAGER
    # --------------------------------------------------------

    response = requests.post(

        f"{ALERTMANAGER_URL}/api/v2/silences",

        json=silence,

        timeout=10

    )


    # --------------------------------------------------------
    # CHECK RESPONSE
    # --------------------------------------------------------

    response.raise_for_status()


    result = response.json()

    silence_id = result.get(
        "silenceID"
    )


    print(
        f"Alertmanager silence created: {silence_id}"
    )


    return silence_id


# ============================================================
# GET ALERT BY FINGERPRINT
# ============================================================

def get_alert_by_fingerprint(fingerprint):

    """
    Find an active alert in Alertmanager using fingerprint.
    """

    response = requests.get(

        f"{ALERTMANAGER_URL}/api/v2/alerts",

        timeout=10

    )

    response.raise_for_status()

    alerts = response.json()


    for alert in alerts:

        if alert.get("fingerprint") == fingerprint:

            return alert


    return None


# ============================================================
# ACCEPT BUTTON
# ============================================================

@bolt_app.action("accept_alert")
def accept_alert(ack, body, client):

    # --------------------------------------------------------
    # ACK SLACK REQUEST IMMEDIATELY
    # --------------------------------------------------------

    ack()


    try:

        # ----------------------------------------------------
        # SLACK USER
        # ----------------------------------------------------

        user_id = body["user"]["id"]

        user_name = body["user"].get(
            "name",
            "Unknown"
        )


        # ----------------------------------------------------
        # SLACK MESSAGE
        # ----------------------------------------------------

        channel_id = body["channel"]["id"]

        message_ts = body["message"]["ts"]


        # ----------------------------------------------------
        # ALERT FINGERPRINT
        # ----------------------------------------------------

        fingerprint = body["actions"][0].get(
            "value",
            ""
        )


        print(
            f"ACCEPT clicked by {user_name} "
            f"(user_id={user_id})"
        )

        print(
            f"Alert fingerprint: {fingerprint}"
        )


        # ----------------------------------------------------
        # GET ALERT FROM ALERTMANAGER
        # ----------------------------------------------------

        alert = get_alert_by_fingerprint(
            fingerprint
        )


        if not alert:

            print(
                "Alert not found in Alertmanager."
            )


            client.chat_update(

                channel=channel_id,

                ts=message_ts,

                text="Alert no longer active",

                blocks=[

                    {
                        "type": "section",

                        "text": {
                            "type": "mrkdwn",

                            "text": (
                                "⚠️ *Alert no longer active*\n\n"
                                "The alert could not be found "
                                "in Alertmanager."
                            )
                        }
                    }

                ]

            )

            return


        # ----------------------------------------------------
        # GET ALERT LABELS
        # ----------------------------------------------------

        labels = alert.get(
            "labels",
            {}
        )


        # ----------------------------------------------------
        # CREATE 4-HOUR SILENCE
        # ----------------------------------------------------

        silence_id = create_alertmanager_silence(

            labels,

            user_name

        )


        # ----------------------------------------------------
        # CALCULATE RE-NOTIFICATION TIME
        # ----------------------------------------------------

        renotify_time = (
            datetime.now(timezone.utc)
            + timedelta(hours=4)
        )


        # ----------------------------------------------------
        # UPDATE SLACK MESSAGE
        # ----------------------------------------------------

        client.chat_update(

            channel=channel_id,

            ts=message_ts,

            text="Alert acknowledged",

            blocks=[

                {

                    "type": "section",

                    "text": {

                        "type": "mrkdwn",

                        "text": (

                            "🚨 *ALERT FIRING — "
                            "Production Monitoring*\n\n"

                            "✅ *Acknowledged*\n\n"

                            f"*Acknowledged by:* "
                            f"{user_name}\n\n"

                            f"*Acknowledged at:* "
                            f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"

                            "*Re-notification:* "
                            "in 4 hours if still firing\n\n"

                            f"*Silence ID:* `{silence_id}`"

                        )

                    }

                }

            ]

        )


        print(
            f"Alert successfully acknowledged by "
            f"{user_name}"
        )

        print(
            f"Silence ID: {silence_id}"
        )

        print(
            f"Re-notification after: "
            f"{renotify_time.isoformat()}"
        )


    except Exception as e:

        print(
            f"ERROR while accepting alert: {e}"
        )


# ============================================================
# REJECT BUTTON
# ============================================================

@bolt_app.action("reject_alert")
def reject_alert(ack, body, client):

    # --------------------------------------------------------
    # ACK SLACK REQUEST
    # --------------------------------------------------------

    ack()


    try:

        channel_id = body["channel"]["id"]

        message_ts = body["message"]["ts"]


        print(
            "REJECT clicked"
        )


        # ----------------------------------------------------
        # IMPORTANT:
        # DO NOT CREATE SILENCE
        # ----------------------------------------------------

        client.chat_update(

            channel=channel_id,

            ts=message_ts,

            text="Alert rejected",

            blocks=[

                {

                    "type": "section",

                    "text": {

                        "type": "mrkdwn",

                        "text": (

                            "🚨 *ALERT FIRING — "
                            "Production Monitoring*\n\n"

                            "⚠️ *Alert rejected*\n\n"

                            "*Status:* 🔴 FIRING\n\n"

                            "Alert remains unacknowledged. "
                            "Normal Alertmanager "
                            "notifications will continue."

                        )

                    }

                }

            ]

        )


    except Exception as e:

        print(
            f"ERROR while rejecting alert: {e}"
        )


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route(
    "/health",
    methods=["GET"]
)
def health():

    return jsonify(
        {
            "status": "ok"
        }
    )


# ============================================================
# TEST SLACK
# ============================================================

@app.route(
    "/test-slack",
    methods=["GET"]
)
def test_slack():

    warning = slack.chat_postMessage(

        channel=WARNING_CHANNEL,

        text="Promax Monitoring — WARNING channel test"

    )


    critical = slack.chat_postMessage(

        channel=CRITICAL_CHANNEL,

        text="Promax Monitoring — CRITICAL channel test"

    )


    return jsonify(

        {

            "warning_ok":
                warning["ok"],

            "critical_ok":
                critical["ok"]

        }

    )


# ============================================================
# ALERTMANAGER WEBHOOK
# ============================================================

@app.route(
    "/alertmanager",
    methods=["POST"]
)
def alertmanager():

    try:

        data = request.get_json()


        print(
            "========================================"
        )

        print(
            "Alertmanager webhook received"
        )

        print(
            "========================================"
        )

        print(
            data
        )


        status = data.get(
            "status",
            "firing"
        )


        # ----------------------------------------------------
        # PROCESS EVERY ALERT
        # ----------------------------------------------------

        for alert in data.get(
            "alerts",
            []
        ):

            labels = alert.get(
                "labels",
                {}
            )


            severity = labels.get(
                "severity",
                "warning"
            )


            # ------------------------------------------------
            # SELECT CHANNEL
            # ------------------------------------------------

            if severity == "critical":

                channel = CRITICAL_CHANNEL

            else:

                channel = WARNING_CHANNEL


            # ------------------------------------------------
            # BUILD MESSAGE
            # ------------------------------------------------

            text, blocks = build_alert_message(

                alert,

                status

            )


            # ------------------------------------------------
            # SEND SLACK MESSAGE
            # ------------------------------------------------

            response = slack.chat_postMessage(

                channel=channel,

                text=text,

                blocks=blocks

            )


            print(

                f"Slack message sent: "
                f"channel={channel}, "
                f"ts={response['ts']}"

            )


        return jsonify(
            {
                "ok": True
            }
        )


    except Exception as e:

        print(
            f"ERROR processing Alertmanager webhook: {e}"
        )


        return jsonify(

            {
                "ok": False,
                "error": str(e)
            }

        ), 500


# ============================================================
# SOCKET MODE
# ============================================================

def start_socket_mode():

    print(
        "Starting Slack Socket Mode..."
    )


    handler = SocketModeHandler(

        bolt_app,

        os.environ.get(
            "SLACK_APP_TOKEN"
        )

    )


    handler.start()


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    # --------------------------------------------------------
    # START SOCKET MODE IN BACKGROUND
    # --------------------------------------------------------

    socket_thread = threading.Thread(

        target=start_socket_mode,

        daemon=True

    )

    socket_thread.start()


    # --------------------------------------------------------
    # START FLASK
    # --------------------------------------------------------

    app.run(

        host="0.0.0.0",

        port=5000

    )
