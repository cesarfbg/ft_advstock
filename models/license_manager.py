import hashlib
import logging
import os

import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

LICENSE_API_URL = 'https://admin.feraltech.co/api/v1/verify-license'
APP_CODE = 'advanced_stock_reports'
APP_VERSION = '16.0'


class LicenseManager(models.AbstractModel):
    _name = 'advanced.stock.reports.license'
    _description = 'Inventario Avanzado - License Manager'

    # ------------------------------------------------------------------
    # Anti-Tamper: SHA-256 of this very file
    # ------------------------------------------------------------------
    @api.model
    def _get_integrity_hash(self):
        file_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'license_manager.py',
        )
        with open(file_path, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()

    # ------------------------------------------------------------------
    # API validation
    # ------------------------------------------------------------------
    @api.model
    def validate_license(self):
        """Send license payload to the API and cache the result."""
        ICP = self.env['ir.config_parameter'].sudo()
        token = self.env.company.license_token

        if not token:
            _logger.warning('[LIC] No token configured for company %s', self.env.company.name)
            ICP.set_param('advanced_stock_reports.license_status', 'no_token')
            ICP.set_param(
                'advanced_stock_reports.license_last_check',
                fields.Datetime.to_string(fields.Datetime.now()),
            )
            return False

        integrity_hash = self._get_integrity_hash()
        payload = {
            'token': token,
            'app_code': APP_CODE,
            'app_version': APP_VERSION,
            'integrity_hash': integrity_hash,
        }
        headers = {'Content-Type': 'application/json'}

        _logger.info('[LIC] >>> REQUEST to %s', LICENSE_API_URL)
        _logger.info('[LIC] >>> Payload: %s', {
            **payload,
            'token': token[:8] + '...' if len(token) > 8 else '***',
        })

        try:
            response = requests.post(LICENSE_API_URL, json=payload, headers=headers, timeout=10)
            _logger.info('[LIC] <<< HTTP %s', response.status_code)
            _logger.info('[LIC] <<< Body: %s', response.text[:500])
            response.raise_for_status()
            result = response.json()

            # API responds: {"valid": true/false, "message": "...", "expiration": ...}
            is_valid = result.get('valid', False)
            api_message = result.get('message', '')
            expiration = result.get('expiration')

            if is_valid:
                status = 'active'
                if expiration:
                    ICP.set_param('advanced_stock_reports.license_expiration', expiration)
            else:
                # Map API messages to internal status codes
                msg_lower = api_message.lower()
                if 'invalid token' in msg_lower:
                    status = 'invalid_token'
                elif 'not applicable' in msg_lower:
                    status = 'not_applicable'
                elif 'unknown app version' in msg_lower:
                    status = 'unknown_version'
                elif 'missing' in msg_lower:
                    status = 'missing_fields'
                else:
                    status = 'rejected'
                _logger.warning('[LIC] API rejected: %s', api_message)

        except Exception as exc:
            _logger.warning('[LIC] <<< Request failed: %s', exc)
            status = ICP.get_param(
                'advanced_stock_reports.license_status', 'error'
            )

        _logger.info('[LIC] Final status: %s', status)
        ICP.set_param('advanced_stock_reports.license_status', status)
        ICP.set_param(
            'advanced_stock_reports.license_last_check',
            fields.Datetime.to_string(fields.Datetime.now()),
        )
        return status == 'active'

    # ------------------------------------------------------------------
    # Public check (called before accessing reports)
    # ------------------------------------------------------------------
    @api.model
    def check_license(self):
        """Verify license for all selected companies.

        Raises UserError if any selected company doesn't have an active license.
        """
        # Get selected companies from context (multi-company support)
        allowed_company_ids = self.env.context.get('allowed_company_ids', [self.env.company.id])
        companies = self.env['res.company'].browse(allowed_company_ids)

        invalid_companies = []
        messages_by_company = {}

        for company in companies:
            # Check license for this specific company
            status = self._check_company_license(company)

            if status != 'active':
                invalid_companies.append(company)
                messages_by_company[company.name] = self._get_license_error_message(status)

        if invalid_companies:
            # Build error message listing all companies with license issues
            if len(invalid_companies) == 1:
                company_names = invalid_companies[0].name
                msg = _('La compañía "%s" no tiene una licencia válida:\n%s') % (
                    company_names,
                    messages_by_company[invalid_companies[0].name]
                )
            else:
                company_list = '\n'.join([
                    '• %s: %s' % (c.name, messages_by_company[c.name])
                    for c in invalid_companies
                ])
                msg = _('Las siguientes compañías no tienen licencias válidas:\n\n%s') % company_list

            raise UserError(msg)

        return True

    @api.model
    def _check_company_license(self, company):
        """Check license status for a specific company."""
        ICP = self.env['ir.config_parameter'].sudo()
        cache_key_status = 'advanced_stock_reports.license_status.%s' % company.id
        cache_key_check = 'advanced_stock_reports.license_last_check.%s' % company.id

        last_check_str = ICP.get_param(cache_key_check)
        status = ICP.get_param(cache_key_status, 'pending')

        needs_refresh = True
        if last_check_str and status == 'active':
            try:
                last_dt = fields.Datetime.from_string(last_check_str)
                now = fields.Datetime.now()
                # Cache valid for 4 hours (14400 seconds)
                if last_dt and (now - last_dt).total_seconds() < 14400:
                    needs_refresh = False
            except Exception:
                pass

        if needs_refresh:
            _logger.info('[LIC] Checking license for company %s (id=%s)', company.name, company.id)
            status = self._validate_company_license(company)

        return status

    @api.model
    def _validate_company_license(self, company):
        """Validate license for a specific company against the API."""
        ICP = self.env['ir.config_parameter'].sudo()
        token = company.license_token

        cache_key_status = 'advanced_stock_reports.license_status.%s' % company.id
        cache_key_check = 'advanced_stock_reports.license_last_check.%s' % company.id

        if not token:
            _logger.warning('[LIC] No token configured for company %s', company.name)
            ICP.set_param(cache_key_status, 'no_token')
            ICP.set_param(cache_key_check, fields.Datetime.to_string(fields.Datetime.now()))
            return 'no_token'

        integrity_hash = self._get_integrity_hash()
        payload = {
            'token': token,
            'app_code': APP_CODE,
            'app_version': APP_VERSION,
            'integrity_hash': integrity_hash,
        }
        headers = {'Content-Type': 'application/json'}

        _logger.info('[LIC] >>> REQUEST to %s for company %s', LICENSE_API_URL, company.name)

        try:
            response = requests.post(LICENSE_API_URL, json=payload, headers=headers, timeout=10)
            _logger.info('[LIC] <<< HTTP %s', response.status_code)
            response.raise_for_status()
            result = response.json()

            is_valid = result.get('valid', False)
            api_message = result.get('message', '')
            expiration = result.get('expiration')

            if is_valid:
                status = 'active'
                if expiration:
                    ICP.set_param('advanced_stock_reports.license_expiration.%s' % company.id, expiration)
            else:
                msg_lower = api_message.lower()
                if 'invalid token' in msg_lower:
                    status = 'invalid_token'
                elif 'not applicable' in msg_lower:
                    status = 'not_applicable'
                elif 'unknown app version' in msg_lower:
                    status = 'unknown_version'
                elif 'missing' in msg_lower:
                    status = 'missing_fields'
                else:
                    status = 'rejected'
                _logger.warning('[LIC] API rejected for company %s: %s', company.name, api_message)

        except Exception as exc:
            _logger.warning('[LIC] Request failed for company %s: %s', company.name, exc)
            status = ICP.get_param(cache_key_status, 'error')

        _logger.info('[LIC] Final status for company %s: %s', company.name, status)
        ICP.set_param(cache_key_status, status)
        ICP.set_param(cache_key_check, fields.Datetime.to_string(fields.Datetime.now()))
        return status

    @api.model
    def _get_license_error_message(self, status):
        """Get user-friendly error message for a license status."""
        messages = {
            'no_token': _('No se ha configurado el token de licencia. Vaya a Ajustes > Inventario Avanzado.'),
            'invalid_token': _('El token de licencia no es válido.'),
            'not_applicable': _('El token no corresponde a esta aplicación.'),
            'unknown_version': _('Versión de la aplicación no reconocida por el servidor.'),
            'missing_fields': _('Error en la solicitud de licencia (campos faltantes).'),
            'rejected': _('La licencia fue rechazada por el servidor.'),
            'expired': _('La licencia ha expirado. Contacte a Feral Tech.'),
            'tampered': _('Se detectó una modificación no autorizada del módulo.'),
            'error': _('No se pudo conectar al servidor de licencias.'),
        }
        return messages.get(status, _('Licencia no válida (estado: %s).') % status)
