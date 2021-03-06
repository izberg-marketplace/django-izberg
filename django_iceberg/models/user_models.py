# -*- coding: utf-8 -*-

import json
from django.db import models
from django.conf import settings
from django.utils.translation import ugettext_lazy as _


from .base_models import IcebergBaseModel

from icebergsdk.api import IcebergAPI
from django_iceberg.conf import ConfigurationDebug, ConfigurationDebugSandbox,\
                                ConfigurationSandbox, ConfigurationSandboxStage,\
                                ConfigurationStage, ConfigurationProd

class UserIcebergModel(IcebergBaseModel):

    user = models.ForeignKey(settings.AUTH_USER_MODEL, blank=True, null=True)

    iceberg_username = models.CharField(max_length = 255, null = True, blank = True)

    access_token = models.CharField(max_length = 255, null = True, blank = True)

    sso_data = models.TextField(_('Single Sign On Data'),
        null = True, blank = True, help_text = _('Will keep SSO data for fast access'))

    application_namespace = models.CharField(_('Application Namespace'),
        max_length = 255, null = True, blank = True,
        help_text = _('Allow Connection with several Applications'))

    language = models.CharField(default="en", max_length = 10) # ISO

    # Shopping Preference
    shipping_country = models.CharField(default="FR", max_length = 10) # ISO
    currency = models.CharField(default="EUR", max_length = 3) # ISO


    def switch_env(self, new_env):
        self.environment = new_env
        ## clearing sso data that wont be valid anymore on new_env
        self.sso_data = None
        self.access_token = None
        self.save()

    def get_conf(self):
        enviro = self.environment
        if getattr(settings, 'ICEBERG_USE_LOCAL', False):
            if not enviro:
                enviro = getattr(settings, 'ICEBERG_DEFAULT_ENVIRO', None)

            if enviro == UserIcebergModel.ICEBERG_SANDBOX:
                conf = ConfigurationDebugSandbox
            else:
                conf = ConfigurationDebug
        else:
            if not enviro:
                enviro = getattr(settings, 'ICEBERG_DEFAULT_ENVIRO', None)

            if enviro == UserIcebergModel.ICEBERG_SANDBOX:
                conf = ConfigurationSandbox
            elif enviro == UserIcebergModel.ICEBERG_SANDBOX_STAGE:
                conf = ConfigurationSandboxStage
            elif enviro == UserIcebergModel.ICEBERG_STAGE:
                conf = ConfigurationStage
            else: # None or UserIcebergModel.ICEBERG_PROD
                conf = ConfigurationProd

        return conf

    def get_api_handler(self):
        conf = self.get_conf()
        api_handler = IcebergAPI(conf = conf, username = self.iceberg_username, access_token = self.access_token)
        return api_handler


    def sync_shopping_preferences(self):
        """
        Will forward shopping preference to Iceberg
        """
        api_handler = self.get_api_handler()
        api_handler._sso_response = json.loads(self.sso_data)
        shopping_preference = api_handler.me().shopping_preference
        shopping_preference.country = api_handler.Country.search({"code": self.shipping_country})[0][0]
        shopping_preference.currency = self.currency
        shopping_preference.save()
