import contextlib
from io import StringIO
from unittest.mock import patch

import pytest
import responses

from tests.search.v2.test_hosts import VIEW_HOST_JSON
from tests.utils import CensysTestCase

from censys.cli import main as cli_main
from censys.cli.commands.hnri import CensysHNRI
from censys.common.exceptions import CensysCLIException


class CensysCliHNRITest(CensysTestCase):
    IPIFY_URL = "https://api.ipify.org?format=json"
    IP_ADDRESS = "8.8.8.8"

    def setUp(self):
        super().setUp()
        self.api = CensysHNRI(self.api_id, self.api_secret)
        self.base_url = self.api.index._api_url

    @patch(
        "argparse._sys.argv",
        ["censys", "hnri"] + CensysTestCase.cli_args,
    )
    @patch(
        "censys.cli.commands.hnri.CensysHNRI.get_current_ip", return_value=IP_ADDRESS
    )
    def test_hnri_medium(self, mock_ip):
        response = VIEW_HOST_JSON.copy()
        response["result"]["services"] = [
            {"port": 443, "service_name": "HTTPS"},
            {"port": 53, "service_name": "DNS"},
        ]
        self.responses.add(
            responses.GET,
            f"{self.base_url}/hosts/{self.IP_ADDRESS}",
            status=200,
            json=response,
        )

        temp_stdout = StringIO()
        with contextlib.redirect_stdout(temp_stdout):
            cli_main()

        stdout = temp_stdout.getvalue().strip()
        assert self.IP_ADDRESS in stdout
        assert "Medium Risks Found" in stdout
        assert "HTTPS" in stdout
        assert "443" in stdout
        assert "DNS" in stdout
        assert "53" in stdout

    @patch(
        "argparse._sys.argv",
        ["censys", "hnri"] + CensysTestCase.cli_args,
    )
    @patch(
        "censys.cli.commands.hnri.CensysHNRI.get_current_ip", return_value=IP_ADDRESS
    )
    def test_hnri_no_medium(self, mock_ip):
        response = VIEW_HOST_JSON.copy()
        response["result"]["services"] = [{"port": 23, "service_name": "VNC"}]
        self.responses.add(
            responses.GET,
            f"{self.base_url}/hosts/{self.IP_ADDRESS}",
            status=200,
            json=response,
        )

        temp_stdout = StringIO()
        with contextlib.redirect_stdout(temp_stdout):
            cli_main()

        stdout = temp_stdout.getvalue().strip()
        assert self.IP_ADDRESS in stdout
        assert "High Risks Found" in stdout
        assert "VNC" in stdout
        assert "23" in stdout
        assert "You don't have any Medium Risks in your network" in stdout

    @patch(
        "argparse._sys.argv",
        ["censys", "hnri"] + CensysTestCase.cli_args,
    )
    @patch(
        "censys.cli.commands.hnri.CensysHNRI.get_current_ip", return_value=IP_ADDRESS
    )
    def test_hnri_not_found(self, mock_ip):
        response = VIEW_HOST_JSON.copy()
        response["result"]["services"] = []
        self.responses.add(
            responses.GET,
            f"{self.base_url}/hosts/{self.IP_ADDRESS}",
            status=200,
            json=response,
        )

        temp_stdout = StringIO()
        with contextlib.redirect_stdout(temp_stdout):
            cli_main()

        stdout = temp_stdout.getvalue().strip()
        assert self.IP_ADDRESS in stdout
        assert "No Risks were found on your network" in stdout

    def test_get_current_ip(self):
        self.responses.add(
            responses.GET,
            self.IPIFY_URL,
            status=200,
            json={"ip": self.IP_ADDRESS},
        )
        ip_address = self.api.get_current_ip()
        assert ip_address == self.IP_ADDRESS

    def test_no_risks(self):
        with pytest.raises(CensysCLIException):
            self.api.risks_to_string([], [])

    @patch(
        "argparse._sys.argv",
        ["censys", "hnri", "--open"],
    )
    @patch("censys.cli.commands.view.webbrowser.open")
    def test_open(self, mock_open):
        with pytest.raises(SystemExit, match="0"):
            cli_main()
        mock_open.assert_called_with("https://search.censys.io/me")
