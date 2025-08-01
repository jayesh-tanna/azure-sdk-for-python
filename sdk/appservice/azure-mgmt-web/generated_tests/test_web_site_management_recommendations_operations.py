# coding=utf-8
# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# Code generated by Microsoft (R) AutoRest Code Generator.
# Changes may cause incorrect behavior and will be lost if the code is regenerated.
# --------------------------------------------------------------------------
import pytest
from azure.mgmt.web.v2024_11_01 import WebSiteManagementClient

from devtools_testutils import AzureMgmtRecordedTestCase, RandomNameResourceGroupPreparer, recorded_by_proxy

AZURE_LOCATION = "eastus"


@pytest.mark.skip("you may need to update the auto-generated test case before run it")
class TestWebSiteManagementRecommendationsOperations(AzureMgmtRecordedTestCase):
    def setup_method(self, method):
        self.client = self.create_mgmt_client(WebSiteManagementClient)

    @RandomNameResourceGroupPreparer(location=AZURE_LOCATION)
    @recorded_by_proxy
    def test_recommendations_list(self, resource_group):
        response = self.client.recommendations.list(
            api_version="2024-11-01",
        )
        result = [r for r in response]
        # please add some check logic here by yourself
        # ...

    @RandomNameResourceGroupPreparer(location=AZURE_LOCATION)
    @recorded_by_proxy
    def test_recommendations_reset_all_filters(self, resource_group):
        response = self.client.recommendations.reset_all_filters(
            api_version="2024-11-01",
        )

        # please add some check logic here by yourself
        # ...

    @RandomNameResourceGroupPreparer(location=AZURE_LOCATION)
    @recorded_by_proxy
    def test_recommendations_disable_recommendation_for_subscription(self, resource_group):
        response = self.client.recommendations.disable_recommendation_for_subscription(
            name="str",
            api_version="2024-11-01",
        )

        # please add some check logic here by yourself
        # ...

    @RandomNameResourceGroupPreparer(location=AZURE_LOCATION)
    @recorded_by_proxy
    def test_recommendations_list_history_for_hosting_environment(self, resource_group):
        response = self.client.recommendations.list_history_for_hosting_environment(
            resource_group_name=resource_group.name,
            hosting_environment_name="str",
            api_version="2024-11-01",
        )
        result = [r for r in response]
        # please add some check logic here by yourself
        # ...

    @RandomNameResourceGroupPreparer(location=AZURE_LOCATION)
    @recorded_by_proxy
    def test_recommendations_list_recommended_rules_for_hosting_environment(self, resource_group):
        response = self.client.recommendations.list_recommended_rules_for_hosting_environment(
            resource_group_name=resource_group.name,
            hosting_environment_name="str",
            api_version="2024-11-01",
        )
        result = [r for r in response]
        # please add some check logic here by yourself
        # ...

    @RandomNameResourceGroupPreparer(location=AZURE_LOCATION)
    @recorded_by_proxy
    def test_recommendations_disable_all_for_hosting_environment(self, resource_group):
        response = self.client.recommendations.disable_all_for_hosting_environment(
            resource_group_name=resource_group.name,
            environment_name="str",
            hosting_environment_name="str",
            api_version="2024-11-01",
        )

        # please add some check logic here by yourself
        # ...

    @RandomNameResourceGroupPreparer(location=AZURE_LOCATION)
    @recorded_by_proxy
    def test_recommendations_reset_all_filters_for_hosting_environment(self, resource_group):
        response = self.client.recommendations.reset_all_filters_for_hosting_environment(
            resource_group_name=resource_group.name,
            environment_name="str",
            hosting_environment_name="str",
            api_version="2024-11-01",
        )

        # please add some check logic here by yourself
        # ...

    @RandomNameResourceGroupPreparer(location=AZURE_LOCATION)
    @recorded_by_proxy
    def test_recommendations_get_rule_details_by_hosting_environment(self, resource_group):
        response = self.client.recommendations.get_rule_details_by_hosting_environment(
            resource_group_name=resource_group.name,
            hosting_environment_name="str",
            name="str",
            api_version="2024-11-01",
        )

        # please add some check logic here by yourself
        # ...

    @RandomNameResourceGroupPreparer(location=AZURE_LOCATION)
    @recorded_by_proxy
    def test_recommendations_disable_recommendation_for_hosting_environment(self, resource_group):
        response = self.client.recommendations.disable_recommendation_for_hosting_environment(
            resource_group_name=resource_group.name,
            environment_name="str",
            name="str",
            hosting_environment_name="str",
            api_version="2024-11-01",
        )

        # please add some check logic here by yourself
        # ...

    @RandomNameResourceGroupPreparer(location=AZURE_LOCATION)
    @recorded_by_proxy
    def test_recommendations_list_history_for_web_app(self, resource_group):
        response = self.client.recommendations.list_history_for_web_app(
            resource_group_name=resource_group.name,
            site_name="str",
            api_version="2024-11-01",
        )
        result = [r for r in response]
        # please add some check logic here by yourself
        # ...

    @RandomNameResourceGroupPreparer(location=AZURE_LOCATION)
    @recorded_by_proxy
    def test_recommendations_list_recommended_rules_for_web_app(self, resource_group):
        response = self.client.recommendations.list_recommended_rules_for_web_app(
            resource_group_name=resource_group.name,
            site_name="str",
            api_version="2024-11-01",
        )
        result = [r for r in response]
        # please add some check logic here by yourself
        # ...

    @RandomNameResourceGroupPreparer(location=AZURE_LOCATION)
    @recorded_by_proxy
    def test_recommendations_disable_all_for_web_app(self, resource_group):
        response = self.client.recommendations.disable_all_for_web_app(
            resource_group_name=resource_group.name,
            site_name="str",
            api_version="2024-11-01",
        )

        # please add some check logic here by yourself
        # ...

    @RandomNameResourceGroupPreparer(location=AZURE_LOCATION)
    @recorded_by_proxy
    def test_recommendations_reset_all_filters_for_web_app(self, resource_group):
        response = self.client.recommendations.reset_all_filters_for_web_app(
            resource_group_name=resource_group.name,
            site_name="str",
            api_version="2024-11-01",
        )

        # please add some check logic here by yourself
        # ...

    @RandomNameResourceGroupPreparer(location=AZURE_LOCATION)
    @recorded_by_proxy
    def test_recommendations_get_rule_details_by_web_app(self, resource_group):
        response = self.client.recommendations.get_rule_details_by_web_app(
            resource_group_name=resource_group.name,
            site_name="str",
            name="str",
            api_version="2024-11-01",
        )

        # please add some check logic here by yourself
        # ...

    @RandomNameResourceGroupPreparer(location=AZURE_LOCATION)
    @recorded_by_proxy
    def test_recommendations_disable_recommendation_for_site(self, resource_group):
        response = self.client.recommendations.disable_recommendation_for_site(
            resource_group_name=resource_group.name,
            site_name="str",
            name="str",
            api_version="2024-11-01",
        )

        # please add some check logic here by yourself
        # ...
