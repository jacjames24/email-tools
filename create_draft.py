import sys
sys.path.insert(0, r"C:\workspace\google-tools")
from gmail_tool import authenticate, ACCOUNTS
from googleapiclient.discovery import build
from email.mime.text import MIMEText
import base64

def create_draft(account_name, to, subject, body):
    account = next(a for a in ACCOUNTS if a["name"] == account_name)
    creds = authenticate(account["token"])
    service = build("gmail", "v1", credentials=creds)

    msg = MIMEText(body, "html")
    msg["To"] = to
    msg["Subject"] = subject

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    draft = service.users().drafts().create(
        userId="me",
        body={"message": {"raw": raw}}
    ).execute()
    print(f"Draft created successfully. Draft ID: {draft['id']}")

TH = 'style="background-color:#2c3e50;color:#ffffff;padding:8px 12px;text-align:left;border:1px solid #2c3e50;font-family:Arial,sans-serif;font-size:14px;"'
TD = 'style="padding:8px 12px;border:1px solid #999;font-family:Arial,sans-serif;font-size:14px;"'
TD_ALT = 'style="padding:8px 12px;border:1px solid #999;background-color:#f2f2f2;font-family:Arial,sans-serif;font-size:14px;"'

BODY = f"""<div style="font-family:Arial,sans-serif;font-size:14px;color:#222;line-height:1.6;">

<p>Hello Laila and everyone,</p>

<p>Hope this email finds you well.</p>

<p>Attached to this email is the result of my sanity testing and observations for AccuRad iOS 2.11.0(4), AccuRad Android 2.11.0, and RDS Android 2.1.0.7, covering the period of March 21 to March 29, 2026.</p>

<p>That said, please refer to the test parameters as seen below.</p>

<table style="border-collapse:collapse;width:100%;margin:16px 0;">
  <thead>
    <tr>
      <th {TH}>Item</th>
      <th {TH}>AccuRad Android</th>
      <th {TH}>AccuRad iOS</th>
      <th {TH}>RDS Android</th>
    </tr>
  </thead>
  <tbody>
    <tr><td {TD}>App version</td><td {TD}>2.11.0</td><td {TD}>2.11.0(4)</td><td {TD}>2.1.0.7</td></tr>
    <tr><td {TD_ALT}>OS version</td><td {TD_ALT}>Android 16</td><td {TD_ALT}>iOS 26.3.1(a)</td><td {TD_ALT}>Android 16</td></tr>
    <tr><td {TD}>Device model</td><td {TD}>Samsung Galaxy S22</td><td {TD}>iPhone 12 Pro Max</td><td {TD}>Samsung Galaxy S22</td></tr>
    <tr><td {TD_ALT}>Device usage</td><td {TD_ALT}>Secondary device</td><td {TD_ALT}>Daily driver</td><td {TD_ALT}>Secondary device</td></tr>
    <tr><td {TD}>Connection type</td><td {TD}>Opened</td><td {TD}>Opened</td><td {TD}>N/A</td></tr>
  </tbody>
</table>

<h3 style="color:#2c3e50;margin-top:24px;margin-bottom:4px;">AccuRad iOS &ndash; Observations</h3>

<p>Testing for AccuRad iOS version 2.11.0(4) was carried out on the iPhone 12 Pro Max as a daily driver throughout the testing period.</p>

<p>Overall, connectivity with PRD 000003 was relatively okay. While brief intermittent disconnections occurred at various points, the app consistently re-established the Bluetooth connection on its own without requiring manual intervention. It is worth noting that I test in a consistently crowded environment with many nearby Bluetooth devices, which naturally adds some pressure to BT stability.</p>

<p>Alarm capture was functioning as expected across the testing period. Multiple High Alarms were recorded across several days, including a cluster on March 25 between 9:14 AM and 9:42 AM registering 7.4, 11.9, and 9.8 microRem/h. Low Alarm capture was also verified on March 27 (3.3 microRem/h). All alarm events were accurately timestamped and categorized throughout the period.</p>

<p>The 30-MIN graph view generally reflected connection status, with dense data during periods of sustained connectivity and sparse or empty segments during brief disconnections. No critical bugs or unexpected behaviors were observed during this sanity test.</p>

<h3 style="color:#2c3e50;margin-top:24px;margin-bottom:4px;">AccuRad Android &ndash; Observations</h3>

<p>Testing for AccuRad Android version 2.11.0 was carried out on the Samsung Galaxy S22 as a secondary device, with the connection open throughout.</p>

<p>The Android version generally demonstrated strong background Bluetooth performance. The 30-MIN graph was dense and continuous across most days, including March 23, March 25, March 27, March 28, and March 29, reflecting stable and uninterrupted PRD connectivity (ACR00002F). Alarm capture was consistent throughout, with High Alarms logged across all active testing days.</p>

<p>It is worth noting that on March 24 and March 26, the graph showed significantly sparse data during daytime hours, with only isolated data points recorded rather than a continuous line. Connectivity appeared to resume later in the evening on both days, as alarms were still captured during those windows. The daytime gaps may have been due to the device being out of PRD range during those specific periods.</p>

<h3 style="color:#2c3e50;margin-top:24px;margin-bottom:4px;">RDS Android &ndash; Observations</h3>

<p>Testing for RDS Android version 2.1.0.7 was carried out on the Samsung Galaxy S22 as a secondary device.</p>

<p>The RDS-32 (SN: 2001638) connected successfully and was actively logging dose data during the testing session on March 29, with an accumulated dose of 36.7 mrem and a live reading of 4 &micro;Rem/h. The gradient map in the Events tab displayed the route path correctly in cyan, consistent with normal background radiation levels. The 5-MIN dose rate graph showed a step-up pattern starting around 7:10 PM, accurately reflecting dose accumulation during movement. No issues were observed with connectivity, map display, or dose tracking.</p>

<p>As for the screenshots, please refer to the URL below:<br>
<a href="https://drive.google.com/drive/folders/1LnQsik77a_OfSVvKtAixcPMDCTOEzywn?usp=sharing" style="color:#2980b9;">https://drive.google.com/drive/folders/1LnQsik77a_OfSVvKtAixcPMDCTOEzywn?usp=sharing</a></p>

<p>Best regards,<br>Jackie</p>

</div>"""

if __name__ == "__main__":
    create_draft(
        account_name="Freelance",
        to="lmartinez@teamitr.com",
        subject="Re: AccuRad & RDS Testing (Android & iOS)",
        body=BODY
    )
