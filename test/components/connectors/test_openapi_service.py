import json
import pytest
from unittest.mock import MagicMock, Mock
from openapi3 import OpenAPI
from haystack.components.connectors import OpenAPIServiceConnector


@pytest.fixture
def openapi_service_mock():
    return MagicMock(spec=OpenAPI)


@pytest.fixture
def service_auths():
    return {"TestService": "auth_token"}


class TestOpenAPIServiceConnector:
    @pytest.fixture
    def connector(self, service_auths):
        return OpenAPIServiceConnector(service_auths)

    def test_parse_message_invalid_json(self, connector):
        # Test invalid JSON content
        with pytest.raises(ValueError):
            connector._parse_message("invalid json")

    def test_parse_valid_json_message(self):
        connector = OpenAPIServiceConnector()

        # The content format here is OpenAI function calling descriptor
        content = (
            '{"name": "compare_branches","arguments": "{\\n  \\"parameters\\": {\\n   '
            ' \\"basehead\\": \\"main...openapi_container_v5\\",\\n   '
            ' \\"owner\\": \\"deepset-ai\\",\\n    \\"repo\\": \\"haystack\\"\\n  }\\n}"}'
        )
        descriptor = connector._parse_message(content)

        # Assert that the descriptor contains the expected method name and arguments
        assert descriptor["name"] == "compare_branches"
        assert descriptor["arguments"]["parameters"] == {
            "basehead": "main...openapi_container_v5",
            "owner": "deepset-ai",
            "repo": "haystack",
        }
        # but not the requestBody
        assert "requestBody" not in descriptor["arguments"]

        # The content format here is OpenAI function calling descriptor
        content = '{"name": "search","arguments": "{\\n  \\"requestBody\\": {\\n    \\"q\\": \\"haystack\\"\\n  }\\n}"}'
        descriptor = connector._parse_message(content)
        assert descriptor["name"] == "search"
        assert descriptor["arguments"]["requestBody"] == {"q": "haystack"}

        # but not the parameters
        assert "parameters" not in descriptor["arguments"]

    def test_parse_message_missing_fields(self, connector):
        # Test JSON content with missing fields
        with pytest.raises(ValueError):
            connector._parse_message(json.dumps({"name": "test_method"}))

    def test_authenticate_service_invalid(self, connector, openapi_service_mock):
        # Test invalid or missing authentication
        openapi_service_mock.components.securitySchemes = {"apiKey": {}}
        with pytest.raises(ValueError):
            connector._authenticate_service(openapi_service_mock)

    def test_invoke_method_valid(self, connector, openapi_service_mock):
        # Test valid method invocation
        method_invocation_descriptor = {"name": "test_method", "arguments": {}}
        openapi_service_mock.call_test_method = Mock(return_value="response")
        result = connector._invoke_method(openapi_service_mock, method_invocation_descriptor)
        assert result == "response"

    def test_invoke_method_invalid(self, connector, openapi_service_mock):
        # Test invalid method invocation
        method_invocation_descriptor = {"name": "invalid_method", "arguments": {}}
        with pytest.raises(RuntimeError):
            connector._invoke_method(openapi_service_mock, method_invocation_descriptor)
