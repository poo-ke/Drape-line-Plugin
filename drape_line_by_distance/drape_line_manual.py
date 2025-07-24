from PyQt5.QtCore import QVariant
from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterNumber,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFeatureSink,
    QgsFields,
    QgsField,
    QgsFeature,
    QgsGeometry,
    QgsProcessingException,
    QgsFeatureSink,
    QgsPointXY
)

class DrapeLineManual(QgsProcessingAlgorithm):
    INPUT = 'INPUT'
    START = 'START'
    END = 'END'
    UNITS = 'UNITS'
    OUTPUT = 'OUTPUT'

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterFeatureSource(self.INPUT, 'Input line layer', [QgsProcessing.TypeVectorLine]))
        self.addParameter(QgsProcessingParameterNumber(self.START, 'Start Distance', type=QgsProcessingParameterNumber.Double, defaultValue=0.0))
        self.addParameter(QgsProcessingParameterNumber(self.END, 'End Distance', type=QgsProcessingParameterNumber.Double, defaultValue=100.0))
        self.addParameter(QgsProcessingParameterEnum(self.UNITS, 'Units', options=['Meters', 'Feet'], defaultValue=0))
        self.addParameter(QgsProcessingParameterFeatureSink(self.OUTPUT, 'Output line'))

    def name(self): return 'drape_line_manual'
    def displayName(self): return 'Drape Line Manual'
    def group(self): return 'Drape Tools'
    def groupId(self): return 'drapetools'
    def createInstance(self): return DrapeLineManual()

    def extractSegment(self, geom, start, end):
        if geom.isMultipart():
            lines = geom.asMultiPolyline()
        else:
            lines = [geom.asPolyline()]
        segment = []
        dist = 0.0
        for line in lines:
            for i in range(len(line) - 1):
                p1, p2 = line[i], line[i + 1]
                seg_len = QgsPointXY(p1).distance(QgsPointXY(p2))
                if dist + seg_len < start:
                    dist += seg_len
                    continue
                if not segment:
                    ratio = (start - dist) / seg_len
                    segment.append(QgsPointXY(p1.x() + (p2.x() - p1.x()) * ratio, p1.y() + (p2.y() - p1.y()) * ratio))
                if dist + seg_len >= end:
                    ratio = (end - dist) / seg_len
                    segment.append(QgsPointXY(p1.x() + (p2.x() - p1.x()) * ratio, p1.y() + (p2.y() - p1.y()) * ratio))
                    return QgsGeometry.fromPolylineXY(segment)
                segment.append(QgsPointXY(p2))
                dist += seg_len
        return QgsGeometry.fromPolylineXY(segment)

    def processAlgorithm(self, parameters, context, feedback):
        source = self.parameterAsSource(parameters, self.INPUT, context)
        start = self.parameterAsDouble(parameters, self.START, context)
        end = self.parameterAsDouble(parameters, self.END, context)
        units = self.parameterAsEnum(parameters, self.UNITS, context)
        factor = 1.0 if units == 0 else 0.3048

        out_fields = QgsFields()
        for f in source.fields():
            out_fields.append(f)
        out_fields.append(QgsField("length", QVariant.Double))

        (sink, dest_id) = self.parameterAsSink(parameters, self.OUTPUT, context, out_fields, source.wkbType(), source.sourceCrs())

        for feat in source.getFeatures():
            seg_geom = self.extractSegment(feat.geometry(), start * factor, end * factor)
            new_feat = QgsFeature(out_fields)
            new_feat.setGeometry(seg_geom)
            new_feat.setAttributes(feat.attributes() + [seg_geom.length()])
            sink.addFeature(new_feat)
        return {self.OUTPUT: dest_id}
