from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import smtplib  
from email.mime.text import MIMEText          
from email.mime.multipart import MIMEMultipart
import json

def manhattan_distance(lat1, lon1, lat2, lon2):
    return abs(lat1 - lat2) + abs(lon1 - lon2)

def find_closest_mac(dataPoints, assignments):
    min_distance = float('inf')
    target_mac = assignments[0]['devices'][0]['macAddress']
    closest_mac = None

    # find target device
    device = None
    for d in dataPoints:
        if d['ClientMacAddr'] == target_mac:
            device = d
            break
    if not device:
        return
    
    # get all responsible staff mac and email
    staffs_mac_email = {}
    staffs_mac_name = {}
    for a in assignments[0]['states'][0]['staff']:
        staffs_mac_email[a['macAddress']] = a['email']
        staffs_mac_name[a['macAddress']] = a['name']

    for d in dataPoints:
        if d['ClientMacAddr'] not in staffs_mac_email:
            continue
        distance = manhattan_distance(device['lat'], device['lng'], d['lat'], d['lng'])
        if distance < min_distance:
            closest_mac = d['ClientMacAddr']
    
    if closest_mac:
        return closest_mac, staffs_mac_email[closest_mac], staffs_mac_name[closest_mac]

def send_email_alert(closest_mac, device_name, staff_name, staff_email, device_mac, states):
    if closest_mac:
        # Compose email message
        subject = f"Alert: Closest Authorized Personnel to {device_name}"
        body = f"The closest authorized personnel to the {device_name} is you, {staff_name}.\n\n"
        body += f"{device_name} System Alert Details:\n \
                MAC Address: {device_mac}\n \
                Priority: {states[0]['priority']}\n \
                State: {states[0]['name']}\n \
                Alert: {states[0]['name']}\n\n"

        # Concatenate the instructions from the Step1 to Step4 cols
        instructions = ''
        for i in range(len(states[0]['messages'])):
            # step_col = 'Step{}'.format(i+1)
            instructions += '{}. {}\n'.format(i+1, states[0]['messages'][i])

        # Add the instructions to body VAR
        if instructions:
            body += 'Alert Instructions:\n{}'.format(instructions)

        to_emails = [staff_email]

        msg = MIMEMultipart()
        msg['Subject'] = subject
        msg['From'] = "faye.yfan@gmail.com"  # Replace with your email address
        msg['To'] = ', '.join(to_emails)  # Replace with the recipient email addresses separated by commas
        msg.attach(MIMEText(body, 'plain'))

        # Send email via SMTP
        try:
            smtp_server = "smtp.gmail.com"  # Replace with your SMTP server
            smtp_port = 587  # Replace with the appropriate SMTP port
            smtp_username = "faye.yfan@gmail.com"  # Replace with your email address
            smtp_password = "vqkepkyhsujhgejl" # App Password for 2FA
            smtp_connection = smtplib.SMTP(smtp_server, smtp_port)
            smtp_connection.starttls()
            smtp_connection.login(smtp_username, smtp_password)
            smtp_connection.sendmail(msg['From'], to_emails, msg.as_string()) # Use to_emails instead of msg['To']
            smtp_connection.quit()
            print("Alert email sent successfully")
        except Exception as e:
            print("Failed to send alert email:", e)

def load_json(data_string):
    data_string = data_string.replace("'", "\"")  # Replace single quotes with double quotes
    data = json.loads(data_string)
    return data

@csrf_exempt
def receive_data(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        data_points = data.get('dataPoints')
        assignments = data.get('assignments')

        close_mac, staff_email, staff_name = find_closest_mac(data_points, assignments)
        if close_mac:
            send_email_alert(close_mac, assignments[0]['devices'][0]['deviceName'],
                            staff_name, staff_email, assignments[0]['devices'][0]['macAddress'],
                            assignments[0]['states']
                            )

        response_data = {'status': 'success'}
        return JsonResponse(response_data)

    else:
        return JsonResponse({'error': 'Invalid request method'})
