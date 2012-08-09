############################################################
#
# poser2egg.py - Egg File Exporter for Poser Pro
#
# Version 0.1 - Current only exports vertex positions
# and normals. joints are exported, but there are still some
# issues. It currently doesnt export UV coords, textures,
# materials, morphs, weights or animation data, but i have
# plans for all of those.
#
# Run this script inside the Poser in the PoserPython
# interpreter. You should also have Panda3d installed
# on the system. I have only tested it on windows vista
# with Panda3D 1.6.2
# Author: satori(http://www.panda3d.org/forums/profile.php?mode=viewprofile&u=3839), v 0.1
# Author: is_blackhole
#
############################################################
import poser
import os

from utils import *
from egg import EggObject


class Poser2Egg():
    SKIP_OVERWRITE = True
    RECOMPUTE_NORMALS = False
    COMPUTE_TBN = False

    def export(self):
        # get selected figure
        figure = poser.Scene().CurrentFigure()
        #figure = poser.Scene().CurrentActor()
        body_part = False
        assert figure, 'No currently selected figure!'
        figureName = fix_name(figure.Name())
        abort = False
        getSaveFile = poser.DialogFileChooser(2, 0, "Save Egg File", figureName, '', '*.egg')
        getSaveFile.Show()
        fileName = getSaveFile.Path()
        if os.path.exists(fileName) and not Poser2Egg.SKIP_OVERWRITE:
            if not poser.DialogSimple.YesNo("Overwrite " + fileName + "?"):
                abort = True
        if not abort:
            if body_part:
                ikStatusList = self.remove_ik_chains(figure)
            print 'Exporting character:', figureName, 'to', fileName
            try:
                egg_obj = EggObject(figure)
                lines = egg_obj.export()
                output = open(fileName, 'w')
                output.write("".join(lines))
                output.close()
                # write anim
                lines = egg_obj.write_animation()
                #print lines
                output = open(os.path.join(os.path.dirname(fileName), "a.egg"), 'w')
                output.write("".join(lines))
                output.close()
            except IOError, (errno, strerror):
                print 'failed to open file', fileName, 'for writing'
                print "I/O error(%s): %s" % (errno, strerror)
            else:
                print 'finished writing data'
            if body_part:
                self.restore_ik_chains(figure, ikStatusList)
            if Poser2Egg.RECOMPUTE_NORMALS:
                self.recompute_egg_normals(fileName)

    def recompute_egg_normals(self, fileName):
        print "Recompute vertex normals"
        os.chdir(os.path.dirname(fileName))
        cmdln = 'egg-trans "' + fileName + '" -nv 120 -o ' + fileName
        print cmdln
        if os.system(cmdln) == 1:
            print "Error while processing egg file!"

    def remove_ik_chains(self, figure):
        ikStatusList = []
        for i in range(0, figure.NumIkChains()):
            ikStatusList.append(figure.IkStatus(i))
            figure.SetIkStatus(i, 0)  # Turn off
        return ikStatusList

    def restore_ik_chains(self, figure, ikStatusList):
        for i in range(0, figure.NumIkChains()):
            figure.SetIkStatus(i, ikStatusList[i])


exporter = Poser2Egg()
exporter.export()
