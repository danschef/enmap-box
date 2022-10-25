import numpy as np

from enmapboxprocessing.algorithm.importenmapl2aalgorithm import ImportEnmapL2AAlgorithm
from enmapboxprocessing.algorithm.testcase import TestCase
from enmapboxprocessing.rasterreader import RasterReader
from enmapboxtestdata import SensorProducts


class TestImportEnmapL2AAlgorithm(TestCase):

    def test(self):
        alg = ImportEnmapL2AAlgorithm()
        parameters = {
            alg.P_FILE: SensorProducts.EnMAP_L2A_MetadataXml,
            alg.P_OUTPUT_RASTER: self.filename('enmapL2A.vrt'),
        }

        if not self.fileExists(parameters[alg.P_FILE]):
            return

        result = self.runalg(alg, parameters)
        self.assertAlmostEqual(
            -11535788939.968838,
            np.sum(RasterReader(result[alg.P_OUTPUT_RASTER]).array(bandList=[1]), dtype=float)
        )

    def test_OrderByWavelengthOverlapOption(self):

        alg = ImportEnmapL2AAlgorithm()
        parameters = {
            alg.P_FILE: SensorProducts.EnMAP_L2A_MetadataXml,
            alg.P_DETECTOR_OVERLAP: alg.OrderByWavelengthOverlapOption,
            alg.P_OUTPUT_RASTER: self.filename('enmapL2A_OrderByWavelength.vrt'),
        }

        if not self.fileExists(parameters[alg.P_FILE]):
            return

        result = self.runalg(alg, parameters)
        self.assertEqual(224, RasterReader(result[alg.P_OUTPUT_RASTER]).bandCount())

    def test_VnirOnlyOverlapOption(self):

        alg = ImportEnmapL2AAlgorithm()
        parameters = {
            alg.P_FILE: SensorProducts.EnMAP_L2A_MetadataXml,
            alg.P_DETECTOR_OVERLAP: alg.VnirOnlyOverlapOption,
            alg.P_OUTPUT_RASTER: self.filename('enmapL2A_VnirOnly.vrt'),
        }

        if not self.fileExists(parameters[alg.P_FILE]):
            return

        result = self.runalg(alg, parameters)
        reader = RasterReader(result[alg.P_OUTPUT_RASTER])
        self.assertEqual(214, reader.bandCount())

    def test_SwirOnlyOverlapOption(self):

        alg = ImportEnmapL2AAlgorithm()
        parameters = {
            alg.P_FILE: SensorProducts.Enmap.L2A_MetadataXml,
            alg.P_DETECTOR_OVERLAP: alg.SwirOnlyOverlapOption,
            alg.P_OUTPUT_RASTER: self.filename('enmapL2A_SwirOnly.vrt'),
        }

        if not self.fileExists(parameters[alg.P_FILE]):
            return

        result = self.runalg(alg, parameters)
        reader = RasterReader(result[alg.P_OUTPUT_RASTER])
        self.assertEqual(212, reader.bandCount())

    def test_MovingAverageFilterOverlapOption(self):

        alg = ImportEnmapL2AAlgorithm()
        parameters = {
            alg.P_FILE: SensorProducts.Enmap.L2A_MetadataXml,
            alg.P_DETECTOR_OVERLAP: alg.MovingAverageFilterOverlapOption,
            alg.P_OUTPUT_RASTER: self.filename('enmapL2A_MovingAverageFilter.vrt'),
        }

        if not self.fileExists(parameters[alg.P_FILE]):
            return

        result = self.runalg(alg, parameters)
        reader = RasterReader(result[alg.P_OUTPUT_RASTER])
        self.assertEqual(224, reader.bandCount())
