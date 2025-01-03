from enmapbox import initAll
from enmapbox.gui.enmapboxgui import EnMAPBox
from enmapbox.testing import start_app
from hsvcolorrasterrendererapp.hsvcolorrasterrendererdialog import HsvColorRasterRendererDialog
from qgis.core import QgsRasterLayer

qgsApp = start_app()
initAll()

enmapBox = EnMAPBox(None)

layer = QgsRasterLayer(r'D:\data\country_health_2018\country_health_2018.vrt', 'country_health_2018')
mapDock = enmapBox.onDataDropped([layer])

widget = HsvColorRasterRendererDialog()
widget.show()
widget.mLayer.setLayer(layer)
widget.mBand1.setBand(1)
widget.mBand2.setBand(2)
widget.mBand3.setBand(3)

qgsApp.exec_()
