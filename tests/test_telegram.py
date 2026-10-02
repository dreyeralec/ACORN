from telegram.telegram import _post, tel_notify, tel_send_trade, tel_get_updates



def test_send_trade():
    tel_send_trade("NVDA", "BUY", 5, "MKT", None, "testing", 1, 1)
    assert True # test passes if tel_send_trade doesn't raise