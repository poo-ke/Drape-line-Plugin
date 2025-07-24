import csv
from PyQt5.QtCore import QVariant
from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterField,
    QgsProcessingParameterFile,
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

class DrapeLineFromCSV(QgsProcessingAlgorithm):
    INPUT = 'INPUT'
    MATCH_FIELD = 'MATCH_FIELD'
    CSV_FILE = 'CSV_FILE'
    UNITS = 'UNITS'
    OUTPUT = 'OUTPUT'

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterFeatureSource(self.INPUT, 'Input line layer', [QgsProcessing.TypeVectorLine]))
        self.addParameter(QgsProcessingParameterField(self.MATCH_FIELD, 'Matching field in input layer', parentLayerParameterName=self.INPUT))
        self.addParameter(QgsProcessingParameterFile(self.CSV_FILE, 'CSV file with match,start,end', behavior=QgsProcessingParameterFile.File, fileFilter='CSV files (*.csv)'))
        self.addParameter(QgsProcessingParameterEnum(self.UNITS, 'Units', options=['Meters', 'Feet'], defaultValue=0))
        self.addParameter(QgsProcessingParameterFeatureSink(self.OUTPUT, 'Output line'))

    def name(self): return 'drape_line_from_csv'
    def displayName(self): return 'Drape Line from CSV'
    def group(self): return 'Drape Tools'
    def groupId(self): return 'drapetools'
    def createInstance(self): return DrapeLineFromCSV()

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
        layer = self.parameterAsVectorLayer(parameters, self.INPUT, context)
        source = self.parameterAsSource(parameters, self.INPUT, context)
        match_field = self.parameterAsString(parameters, self.MATCH_FIELD, context)
        csv_path = self.parameterAsFile(parameters, self.CSV_FILE, context)
        units = self.parameterAsEnum(parameters, self.UNITS, context)

        unit_factor = 1.0 if units == 0 else 0.3048
        mapping = {}
        with open(csv_path, newline='') as csvfile:
            reader = csv.reader(csvfile)
            next(reader, None)
            for row in reader:
                try:
                    mapping[row[0].strip()] = (float(row[1]) * unit_factor, float(row[2]) * unit_factor)
                except:
                    continue

        out_fields = QgsFields()
        for f in source.fields():
            out_fields.append(f)
        out_fields.append(QgsField("length_seg", QVariant.Double))

        (sink, dest_id) = self.parameterAsSink(parameters, self.OUTPUT, context, out_fields, source.wkbType(), source.sourceCrs())

        for feat in source.getFeatures():
            val = str(feat[match_field]).strip()
            if val not in mapping:
                continue
            start, end = mapping[val]
            seg_geom = self.extractSegment(feat.geometry(), start, end)
            new_feat = QgsFeature(out_fields)
            new_feat.setGeometry(seg_geom)
            attrs = feat.attributes() + [seg_geom.length()]
            new_feat.setAttributes(attrs)
            sink.addFeature(new_feat)
        return {self.OUTPUT: dest_id}
