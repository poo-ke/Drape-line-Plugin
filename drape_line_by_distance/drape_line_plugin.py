from qgis.core import QgsApplication
from .drape_line_provider import DrapedLineProvider

class DrapedLinePlugin:
    def __init__(self, iface):
        self.iface = iface
        self.provider = DrapedLineProvider()

    def initGui(self):
        QgsApplication.processingRegistry().addProvider(self.provider)

    def unload(self):
        QgsApplication.processingRegistry().removeProvider(self.provider)
