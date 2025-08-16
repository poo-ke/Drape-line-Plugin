from PyQt5.QtCore import QVariant
from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterField,
    QgsProcessingParameterString,
    QgsProcessingParameterNumber,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFeatureSink,
    QgsFields,
    QgsField,
    QgsFeature,
    QgsGeometry,
    QgsPointXY
)

class DrapeLineManual(QgsProcessingAlgorithm):
    INPUT = 'INPUT'
    MATCH_FIELD = 'MATCH_FIELD'
    MATCH_VALUE = 'MATCH_VALUE'
    START_DIST = 'START_DIST'
    END_DIST = 'END_DIST'
    UNITS = 'UNITS'
    OUTPUT = 'OUTPUT'

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterFeatureSource(
            self.INPUT, 'Input line layer', [QgsProcessing.TypeVectorLine]))
        self.addParameter(QgsProcessingParameterField(
            self.MATCH_FIELD, 'Matching field in input layer', parentLayerParameterName=self.INPUT))
        self.addParameter(QgsProcessingParameterString(
            self.MATCH_VALUE, 'Value to match'))
        self.addParameter(QgsProcessingParameterNumber(
            self.START_DIST, 'Start distance', type=QgsProcessingParameterNumber.Double, defaultValue=0.0))
        self.addParameter(QgsProcessingParameterNumber(
            self.END_DIST, 'End distance', type=QgsProcessingParameterNumber.Double, defaultValue=100.0))
        self.addParameter(QgsProcessingParameterEnum(
            self.UNITS, 'Units', options=['Meters', 'Feet'], defaultValue=0))
        self.addParameter(QgsProcessingParameterFeatureSink(
            self.OUTPUT, 'Output line'))

    def name(self): return 'drape_line_manual'
    def displayName(self): return 'Drape Line (Manual Input)'
    def group(self): return 'Drape Tools'
    def groupId(self): return 'drapetools'
    def createInstance(self): return DrapeLineManual()

    def shortHelpString(self):
            return """
    <b>Drape Line (Manual Input)</b><br>
    Select a line feature from the input line layer and enter the start and end distances to instantly extract a single segment along its length. All attributes from the source feature are copied to the output, along with the calculated segment length.<br><br>

    <b>Parameters:</b><br>
    <ul>
    <li><b>Input line layer</b>: A polyline layer containing the feature to process.</li>
    <li><b>Matching field in input layer</b>: The attribute field used to find the target feature.</li>
    <li><b>Value to match</b>: The specific value in the matching field that identifies the feature.</li>
    <li><b>Start distance</b>: Distance along the line from the start where the segment begins.</li>
    <li><b>End distance</b>: Distance along the line where the segment ends.</li>
    <li><b>Units</b>: Choose 'Meters' or 'Feet' for distance interpretation.</li>
    </ul>

    <b>Output:</b><br>
    Creates a new line layer containing:<br>
    <ul>
    <li>All original attributes of the matched feature</li>
    <li><b>start_dist</b>: Start distance (in original units)</li>
    <li><b>end_dist</b>: End distance (in original units)</li>
    <li><b>length_seg</b>: Length of the extracted segment (in meters)</li>
    </ul>
    """

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
                    segment.append(QgsPointXY(
                        p1.x() + (p2.x() - p1.x()) * ratio,
                        p1.y() + (p2.y() - p1.y()) * ratio))
                if dist + seg_len >= end:
                    ratio = (end - dist) / seg_len
                    segment.append(QgsPointXY(
                        p1.x() + (p2.x() - p1.x()) * ratio,
                        p1.y() + (p2.y() - p1.y()) * ratio))
                    return QgsGeometry.fromPolylineXY(segment)
                segment.append(QgsPointXY(p2))
                dist += seg_len
        return QgsGeometry.fromPolylineXY(segment)

    def processAlgorithm(self, parameters, context, feedback):
        source = self.parameterAsSource(parameters, self.INPUT, context)
        match_field = self.parameterAsString(parameters, self.MATCH_FIELD, context)
        match_value = self.parameterAsString(parameters, self.MATCH_VALUE, context).strip()
        start = self.parameterAsDouble(parameters, self.START_DIST, context)
        end = self.parameterAsDouble(parameters, self.END_DIST, context)
        units = self.parameterAsEnum(parameters, self.UNITS, context)

        factor = 1.0 if units == 0 else 0.3048
        start *= factor
        end *= factor

        out_fields = QgsFields()
        for f in source.fields():
            out_fields.append(f)

        out_fields.append(QgsField("start_dist", QVariant.Double))
        out_fields.append(QgsField("end_dist", QVariant.Double))
        out_fields.append(QgsField("length_seg", QVariant.Int))

        (sink, dest_id) = self.parameterAsSink(parameters, self.OUTPUT, context,
                                               out_fields, source.wkbType(), source.sourceCrs())

        for feat in source.getFeatures():
            if str(feat[match_field]).strip() != match_value:
                continue

            seg_geom = self.extractSegment(feat.geometry(), start, end)
            if not seg_geom or seg_geom.isEmpty():
                continue

            new_feat = QgsFeature(out_fields)
            new_feat.setGeometry(seg_geom)
            attrs = feat.attributes() + [start / factor, end / factor, seg_geom.length()]
            new_feat.setAttributes(attrs)
            sink.addFeature(new_feat)

        return {self.OUTPUT: dest_id}
