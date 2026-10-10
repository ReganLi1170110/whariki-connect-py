# Admin Params Management Routes
# Lets an admin add/deactivate the values behind dropdowns (classrooms,
# injury types, etc.) without needing direct database access. Only the
# types listed in param_repository.EDITABLE_PARAM_TYPES are actually
# editable here - see that module for why the rest (curriculum_strand,
# attendance_status) are shown read-only instead.

from flask import render_template, request, redirect, url_for, flash
from app import flask_app as app
import app.utils as utils
from app.repository import param_repository


@app.route("/admin/params", methods=["GET"])
@utils.login_required()
@utils.roles_required("Admin")
def admin_params():
    editable = {
        t: param_repository.list_all_params_by_type(t)
        for t in param_repository.EDITABLE_PARAM_TYPES
    }
    readonly = {
        t: param_repository.list_all_params_by_type(t)
        for t in param_repository.READONLY_PARAM_TYPES
    }
    return render_template(
        "admin_params.html",
        editable=editable,
        readonly=readonly,
        strands=param_repository.get_curriculum_strands(),
    )


@app.route("/admin/params/add", methods=["POST"])
@utils.login_required()
@utils.roles_required("Admin")
def admin_add_param():
    param_type = request.form.get("param_type", "").strip()
    param_value = request.form.get("param_value", "").strip()
    description = request.form.get("description", "").strip() or None

    if param_type not in param_repository.EDITABLE_PARAM_TYPES:
        flash("That list isn't editable here.", "danger")
        return redirect(url_for("admin_params"))

    if not param_value:
        flash("Please enter a value to add.", "danger")
        return redirect(url_for("admin_params"))

    param_repository.add_param(param_type, param_value, description)
    flash(f'"{param_value}" has been added.', "success")
    return redirect(url_for("admin_params"))


@app.route("/admin/params/<int:param_id>/deactivate", methods=["POST"])
@utils.login_required()
@utils.roles_required("Admin")
def admin_deactivate_param(param_id):
    param = param_repository.get_param_by_id(param_id)
    if not param or param["param_type"] not in param_repository.EDITABLE_PARAM_TYPES:
        flash("That value can't be managed here.", "danger")
        return redirect(url_for("admin_params"))

    if param["param_type"] == "classroom":
        in_use = param_repository.classroom_in_use(param["param_value"])
        if in_use:
            flash(f'"{param["param_value"]}" is still used by {in_use} '
                  "enrolled child(ren)/staff member(s) - reassign them first.", "danger")
            return redirect(url_for("admin_params"))

    param_repository.deactivate_param(param_id)
    flash(f'"{param["param_value"]}" removed from the list.', "success")
    return redirect(url_for("admin_params"))


@app.route("/admin/params/<int:param_id>/reactivate", methods=["POST"])
@utils.login_required()
@utils.roles_required("Admin")
def admin_reactivate_param(param_id):
    param = param_repository.get_param_by_id(param_id)
    if not param or param["param_type"] not in param_repository.EDITABLE_PARAM_TYPES:
        flash("That value can't be managed here.", "danger")
        return redirect(url_for("admin_params"))

    param_repository.reactivate_param(param_id)
    flash(f'"{param["param_value"]}" restored.', "success")
    return redirect(url_for("admin_params"))
