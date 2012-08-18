#!/usr/bin/env python

import re
import os
import sys

# -----------------
# Detect: Use of OpenLayers.Class
# -----------------
M_CODE = 0
M_COM1_BLOC = 1
M_COM2_BLOC = 2

reJsClass = re.compile(r"^ *(OpenLayers[\.\w]+) *\= *OpenLayers\.Class\(([\w ,\.]*)(\{?)(.*)")
reJsClassStart = re.compile(r"^([\w ,\.]*)(\{?)(.*)")
reJsClassEnd = re.compile(r"^\}\); *$")

reStarTextComBloc =     re.compile(r"^ *\/\*+ *(?! )")
reStarCom2Bloc =        re.compile(r"^ *\/\*\*")
reStarCom1Bloc =        re.compile(r"^ *\/\*")
reEndComBloc =          re.compile(r"\*\/")
reEndSepComBloc =       re.compile(r"\-{30} *\*\/")
reEndLine =             re.compile(r"\n")
reProblematicEndLine =  re.compile(r"\\\n")

def cnvJs(inputFilename, outputFilename):
    print "Class to Pure Js from: %s to: %s " % (inputFilename,outputFilename),

    if not os.path.isfile(inputFilename):
        print "\nProcess aborted due to errors."
        sys.exit('ERROR: Input file "%s" does not exist!' % inputFilename)

    dirOut = os.path.dirname(outputFilename)
    if dirOut == "":
        print "\nProcess aborted due to errors."
        sys.exit('ERROR: Output file "%s" without path!' % outputFilename)

    if not os.path.exists(dirOut):
        os.makedirs(dirOut)
    fOut = open(outputFilename,"w")
    fIn = open(inputFilename)

    mode = M_CODE
    previousProblematicEndLine = False
    
    lineNumber = 0
    
    inheritsList = []
    
    inherits = ""
    classPhase = 0 # 0=No, 1=inherits, 2=body
    className = ""
    classBeguin = ""
    for line in fIn:
        lineNumber += 1
        startCom = -1
        endCom = -1
        if mode == M_CODE and not previousProblematicEndLine:
            oo = reStarCom2Bloc.search(line)
            if oo: 
                startCom = oo.end()
                mode = M_COM2_BLOC
            else:
                oo = reStarCom1Bloc.search(line)
                if oo: 
                    startCom = oo.end()
                    mode = M_COM1_BLOC
                    
            ooClass = reJsClass.search(line)
            if classPhase == 0:
                if ooClass:
                    line = (
                        #"/** @constructor */ " + 
                        ooClass.group(1) + " = function() { " + 
                        ooClass.group(1) + ".prototype.initialize.apply(this,arguments); };" + 
                        ooClass.group(1) + ".prototype = {\n")
                    className = ooClass.group(1)
                    inherits = ooClass.group(2)
                    if ooClass.group(3) == "{":
                        classBeguin = ooClass.group(4)
                        classPhase = 2 # body
                    else:
                        classPhase = 1 # inherits
            elif classPhase == 1:
                if ooClass:
                    print "\nAbnormal termination due to errors."
                    sys.exit("ERROR: Has been found a declaration of a new class before the end of the class \"%s\"" % className)
                oo = reJsClassStart.search(line)
                line = "// " + line
                if oo:
                    inherits += oo.group(1)
                    if oo.group(2) == "{":
                        classBeguin = oo.group(3)
                        classPhase = 2 # body
                    else:
                        classPhase = 1 # inherits
            elif classPhase == 2:
                if ooClass:
                    print "\nAbnormal termination due to errors."
                    sys.exit("ERROR: Has been found a declaration of a new class before the end of the class \"%s\"" % className)
                oo = reJsClassEnd.search(line)
                if oo:
                    line = "}; //classBeguin = \"" + classBeguin + "\"\n"
                    listInh = re.split(r"[ ,]+",inherits)
                    for e in reversed(listInh):
                        if e != "":
                            inheritsList.append("OpenLayers.Util.applyDefaults(" + className + ".prototype, " + e +".prototype);\n")
                    className = ""
                    inherits = ""
                    classBeguin = ""
                    classPhase = 0 # no class
        if mode != M_CODE:
            modeOld = mode
            previousProblematicEndLine = False
            oo = reEndComBloc.search(line)
            if oo: 
                endCom = oo.start()
                mode = M_CODE
            if endCom == -1:
                endCom = reEndLine.search(line).start()
            if startCom >= 0 and startCom <= endCom: # first line 
                startText = reStarTextComBloc.search(line).end()
            if mode == M_CODE: # last line
                if not reEndSepComBloc.search(line): # add separator at last line of block if not found
                    endCom = reEndComBloc.search(line).start()
        fOut.write(line)
        if mode == M_CODE: 
            if reProblematicEndLine.search(line):
                previousProblematicEndLine = True
            else:
                previousProblematicEndLine = False

    # Add inherits of all class in the file
    for e in inheritsList:
        fOut.write(e)
                    
    if classPhase != 0:
        print "\nAbnormal termination due to errors."
        sys.exit("ERROR: Not found the end of the class \"%s\"" % className)
    print "Done!"
    fIn.close()
    fOut.close()
    return outputFilename
    
# -----------------
# main
# -----------------
if __name__ == '__main__':
    cnvJs(sys.argv[1],sys.argv[2])
