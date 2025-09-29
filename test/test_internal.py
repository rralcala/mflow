import unittest
from unittest.mock import MagicMock, patch

from data.internal import QUOTE_CACHE, exchange_rate


class TestExchangeRate(unittest.TestCase):
    def setUp(self):
        QUOTE_CACHE.clear()

    @patch("data.internal.requests.get")
    def test_usdpyg_fetch_and_cache(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"usd": {"pyg": "7300.0"}}
        mock_get.return_value = mock_response

        rate = exchange_rate("USDPYG")
        self.assertEqual(rate, 7300.0)
        self.assertIn("USDPYG", QUOTE_CACHE)
        self.assertEqual(QUOTE_CACHE["USDPYG"], 7300.0)

        # Should use cache, not call requests.get again
        mock_get.reset_mock()
        rate2 = exchange_rate("USDPYG")
        self.assertEqual(rate2, 7300.0)
        mock_get.assert_not_called()

    @patch("data.internal._get_crypto_price")
    def test_btcusd(self, mock_crypto_price):
        mock_crypto_price.return_value = (50000.0, "USD")
        rate = exchange_rate("BTCUSD")
        self.assertEqual(rate, 50000.0)
        mock_crypto_price.assert_called_once_with("BTCUSD")

    @patch("data.internal._get_crypto_price")
    def test_croususd(self, mock_crypto_price):
        mock_crypto_price.return_value = (0.12, "USD")
        rate = exchange_rate("CROUSD")
        self.assertEqual(rate, 0.12)
        mock_crypto_price.assert_called_once_with("CROUSD")

    def test_unknown_currency(self):
        self.assertRaises(ValueError, exchange_rate, "FOOBAR")


if __name__ == "__main__":
    unittest.main()
