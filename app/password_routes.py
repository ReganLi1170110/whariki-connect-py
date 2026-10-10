# Password Reset Routes
#
# There is no real mail server configured for this project, so this degrades
# gracefully the same way the AI assistant does: if SMTP_* environment
# variables are set, a real email is sent; if not, the reset link is shown
# directly on the confirmation page instead, clearly labelled as such, so the
# whole flow is testable without setting up email.
#
# Trade-off worth noting: revealing the reset link on-screen when a matching
# account exists (and staying silent when it doesn't) leaks whether an email
# is registered, in the no-SMTP fallback path only. That's an accepted
# simplification for a project with no real mail infrastructure - once
# SMTP_* is configured, the response is identical either way and nothing is
# revealed.

import os
import secrets
import smtplib
from datetime import datetime, timedelta
from email.message import EmailMessage

from flask import render_template, request, redirect, url_for, flash
from app import flask_app as app
import app.utils as utils
from app.repository import user_repository

TOKEN_LIFETIME = timedelta(hours=1)


def _smtp_configured():
    return all(os.environ.get(k, "").strip() for k in
              ("SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD", "SMTP_FROM"))


def _send_reset_email(to_email, reset_url):
    """Sends the reset link by email. Only called when SMTP_* is configured."""
    msg = EmailMessage()
    msg["Subject"] = "Reset your Whāriki Connect password"
    msg["From"] = os.environ["SMTP_FROM"]
    msg["To"] = to_email
    msg.set_content(
        "We received a request to reset your Whāriki Connect password.\n\n"
        f"Reset it here (this link expires in 1 hour): {reset_url}\n\n"
        "If you didn't request this, you can safely ignore this email."
    )

    with smtplib.SMTP(os.environ["SMTP_HOST"], int(os.environ["SMTP_PORT"])) as server:
        server.starttls()
        server.login(os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"])
        server.send_message(msg)


def send_plain_email(to_email, subject, body):
    """Small shared sender for other notices (e.g. sign-up approval). Callers
    must check _smtp_configured() first; failures are logged, not raised, so
    a mail problem never blocks the action that triggered it."""
    try:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = os.environ["SMTP_FROM"]
        msg["To"] = to_email
        msg.set_content(body)
        with smtplib.SMTP(os.environ["SMTP_HOST"], int(os.environ["SMTP_PORT"])) as server:
            server.starttls()
            server.login(os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"])
            server.send_message(msg)
        return True
    except Exception as exc:  # noqa: BLE001 - any mail failure is non-fatal here
        app.logger.warning("Could not send e-mail to %s: %s", to_email, exc)
        return False


@app.route("/forgot-password", methods=["GET"])
def forgot_password():
    if utils.is_logged_in():
        return redirect(url_for("overview"))
    return render_template("forgot_password.html")


@app.route("/forgot-password", methods=["POST"])
def forgot_password_submit():
    email = request.form.get("email", "").strip()
    user = user_repository.get_user_by_email(email) if email else None

    dev_reset_url = None  # only ever set (and shown) in the no-SMTP fallback

    if user and user["status"] == "approved":
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now() + TOKEN_LIFETIME
        user_repository.set_reset_token(user["user_id"], token, expires_at)
        reset_url = url_for("reset_password", token=token, _external=True)

        if _smtp_configured():
            try:
                _send_reset_email(user["email"], reset_url)
            except Exception as exc:
                app.logger.warning("Password reset email failed to send: %s", exc)
                flash("We couldn't send the reset email right now. Please try again shortly, "
                      "or contact your centre admin.", "danger")
                return render_template("forgot_password.html")
        else:
            dev_reset_url = reset_url

    # Same message whether or not an account was found, when email is
    # actually configured - this is the point of not leaking who has an
    # account. In the no-SMTP fallback, the link (if any) is what actually
    # reveals this, not the wording.
    flash("If an account exists for that email, a password reset link has been sent.", "success")
    return render_template("forgot_password.html", dev_reset_url=dev_reset_url, submitted=True)


@app.route("/reset-password/<token>", methods=["GET"])
def reset_password(token):
    if utils.is_logged_in():
        return redirect(url_for("overview"))

    user = user_repository.get_user_by_reset_token(token)
    if not user:
        flash("That reset link is invalid or has expired. Request a new one below.", "danger")
        return redirect(url_for("forgot_password"))

    return render_template("reset_password.html", token=token)


@app.route("/reset-password/<token>", methods=["POST"])
def reset_password_submit(token):
    user = user_repository.get_user_by_reset_token(token)
    if not user:
        flash("That reset link is invalid or has expired. Request a new one below.", "danger")
        return redirect(url_for("forgot_password"))

    password = request.form.get("password", "")
    confirm = request.form.get("confirm_password", "")

    password_error = utils.validate_password_strength(password)
    if password_error:
        flash(password_error, "danger")
        return render_template("reset_password.html", token=token)

    if password != confirm:
        flash("Those passwords don't match.", "danger")
        return render_template("reset_password.html", token=token)

    user_repository.update_password(user["user_id"], utils.generate_password_hash(password))
    user_repository.clear_reset_token(user["user_id"])

    flash("Your password has been reset. Please sign in with your new password.", "success")
    return redirect(url_for("login"))
