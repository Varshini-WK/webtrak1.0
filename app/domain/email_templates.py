"""
Email HTML templates.

These are Java-parity copies of:
`webtrak/src/main/java/com/webknot/webtrak/constants/EmailTemplates.java`
"""

# NOTE: Placeholders use `%s` to match `String.format(...)` usage in Java.

LEAVE_APPROVAL_REMAINDER = """
<p>Dear <b>%s</b>,</p>
<p>I hope this message finds you well.</p>
<p>This is a courteous reminder regarding the pending approval for the leave request for <b>%s</b>. Your approval is essential for us to proceed.</p>
<p>Kindly take a moment to review and approve at your earliest convenience.</p>
<p>Thank you for your attention to this matter.</p>
<br></br>
<p>Warm regards,</p>
<p><b>Webknot Team</b></p>
"""

NO_TIME_LOGS = """
<p>Hi <b>%s</b>,</p>
<p>You seem to have not logged enough hours on the project - %s  in the last %s working days</p>
<p>Total logged hours - <b>%s</b></p>
<br></br>
<p>Cheers</p>
<p><b>Webtrak | </b><a href="https://webtrak.webknot.in">https://webtrak.webknot.in</a></p>
"""

ONBOARD_INVITE = """
<p>Dear <b>%s</b>,</p>
<p>We are delighted to welcome you to <b>Webknot Technologies</b>! Congratulations on your new role, and we look forward to seeing you thrive as part of our team.</p>
<p>To begin your journey with us, please complete the onboarding process by filling in all the necessary details using the link below:</p>
<p><a href="https://webtrak.webknot.in">https://webtrak.webknot.in</a></p>
<p>This information is essential for us to set up your profile and ensure a smooth start.</p>
<p>If you have any questions or need assistance, feel free to reach out to us at <b>hr@webknot.in</b></p>
<p>Once again, welcome aboard! We are excited to have you with us and wish you great success in your new role.</p>
<br></br>
<p>Warm regards,</p>
<p><b>Webknot Team</b></p>
"""

USER_REQUEST_SUBMIT = """
<p>Dear <b>%s</b>,</p>
<p>This is to inform you that %s has submitted a request for:</p>
<p>• Request Type: <b>%s</b></p>
<p>• Reason: %s</p>
<p>• Duration: <b>%s</b> to <b>%s</b></p>
<br></br>
<p>Please log in to Webtrak <a href="https://webtrak.webknot.in">https://webtrak.webknot.in</a> to review and approve the request.</p>
<br></br>
<p>Warm regards,</p>
<p><b>Webknot Team</b></p>
"""

USER_REQUEST_STATUS_UPDATE = """
<p>Dear <b>%s</b>,</p>
<p>Your %s request has been %s:</p>
<p>• Request Type: <b>%s</b></p>
<p>• Duration: <b>%s</b> to <b>%s</b></p>
<p>• Action By:<b>%s</b></b></p>
<br></br>
<p>Please log in to Webtrak <a href="https://webtrak.webknot.in">https://webtrak.webknot.in</a> for more details.</p>
<br></br>
<p>Warm regards,</p>
<p><b>Webknot Team</b></p>
"""

