import mc
from vplay import Vplay

mc.LogInfo('Init VPLAY')
v = Vplay()

mc.ActivateWindow(14000)
if v.login():
#if True:
    mc.ShowDialogNotification('Logged on')
    #serials = v.get_serials()
#    mc.GetActiveWindow().GetList(120).SetItems(serials)
else:
    mc.ShowDialogOk('Vplay', 'Unable to connect with provided credentials')