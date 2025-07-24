from qgis.core import QgsProcessingProvider
from .drape_line_manual import DrapeLineManual
from .drape_line_from_csv import DrapeLineFromCSV

class DrapedLineProvider(QgsProcessingProvider):
    def loadAlgorithms(self):
        self.addAlgorithm(DrapeLineManual())
        self.addAlgorithm(DrapeLineFromCSV())

    def id(self):
        return "drapeline"

    def name(self):
        return "Drape Line Tools"

    def longName(self):
        return self.name()
