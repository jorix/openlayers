#!/usr/bin/env python

import re
import os
import sys
import logging

# -----------------
# Sintax: OpenLayers Natural Docs --> Closure Compiler jsDoc 
# -----------------

# Translate annotations blocks
syntax ={
# Header Blocks
    "@constructor": {
        "keywords": ["Class:"], # "Constructor:"
        "prefixBlockKeyword": "@constructor",
        "blocks": ["inherits","params","params-optional"],
        "ignores": ["returns"],
        "chks": ["isStartLine"]
    },
    "method": { # No effect: should be studied
        "keywords": ["Method:", "APIMethod:"],
        "blocks": ["params","params-optional","context","returns"],
        "chks": ["isStartLine"]
    },
    "function": { # No effect: should be studied
        "keywords": ["Function:", "APIFunction:"],
        "blocks": ["params","params-optional","context","returns"],
        "requires": ["returns"],
        "chks": ["isStartLine"]
    },    
    "initialize": { # No effect: should be studied
        "keywords": ["Constructor:"],
        "blocks": ["params","params-optional",],
        "ignores": ["returns"],
        "chks": ["isStartLine"]
    },
    "constant": {
        "keywords": ["Constant:"],
        "lines": {
            "lineConv": "itemUnnamed",
            "prefixLine": "@const",
            "maxLines": 1, # forced end of block
        },
        "chks": ["isStartLine"]
    },
    "property": {
        "keywords": ["Property:", "APIProperty:"],
        "ignores": ["params"], # See OpenLayers.Control.DragFeature::onDrag
        "lines": {
            "lineConv": "itemUnnamed",
            "prefixLine": "@type",
            "maxLines": 1, # forced end of block
        },
        "chks": ["isStartLine"]
    },
# Blocks
    "jsDoc": { # See Format/WKT.js:260-349
        "keywords": ["@param ", "@return ", "@returns "],
        "blockConv": "cnvKeywordJsDoc"
    },
    "inherits": {
        "keywords": ["Inherits from: *$", "Inerits from: *$", "Inherits: *$"],
        "lines": {
            "prefixLine": "@extends",
            "lineConv": "itemSuperClass",
            "minLines": 1
            #"maxLines": 1, # Closure Compiler does not understand the multiple-inheritance.
        },
        "chks": ["prevBlank", "requiresHeader"]
    },    
    "params": {
        "keywords": ["Parameters: *$", "Parameter: *$"],
        "lines": {
            "prefixLine": "@param",
            "lineConv": "itemNamed",
            "minLines": 1
        },
        "chks": ["prevBlank", "requiresHeader"]
    },
    "params-optional": { # New block: To debate
        "keywords": ["Optional Parameters: *$", "Optional Parameter: *$"],
        "lines": {
            "prefixLine": "@param",
            "lineConv": "itemOptionalNamed"
        },
        "chks": ["prevBlank", "requiresHeader"]
    },
    "context": {
        "keywords": ["Context: *$"],
        "lines": {
            "lineConv": "itemUnnamed",
            "prefixLine": "@this",
            "minLines": 1
        },
        "chks": ["prevBlank", "requiresHeader"]
    },
    "returns": {
        "keywords": ["Returns: *$", "Return: *$"],
        "lines": {
            "lineConv": "itemUnnamed",
            "prefixLine": "@return",
            "maxLines": 1, # forced end of block
            "minLines": 1
        },
        "chks": ["prevBlank", "requiresHeader"]
    }
}

# Translate types
typesOL = [
    # For DOM types see Closure Compiler source in the folder: closure-compiler/externs
    ("XMLNode",      "Node"), # Closure said: "we put XMLNode properties on Node" (see: ie_dom.js)
    ("DOMElement",   "Element"),
    ("HTMLDOMElement",   "Element"), # Used in: Events.js
    # js types
    ("Number",       "number"),
    ("Integer",      "number"),
    ("int",          "number"), # Used in: Events.js
    ("Float",        "number"),
    ("String",       "string"),
    ("Char",       "string"), # Used in: Filter/Comparison.js
    ("Boolean",      "boolean"),
    ("Function",     "function(...[*])"),
    # Composed types
    (r"Array\((.*)\)",   r"Array.<\1>"), # Array(...) to Array.<...>
    (r"Array\[(.*)\]",   r"Array.<\1>"), # Used in: Popup/Framed.js
    (r"Array\<(.*)\>",   r"Array.<\1>"), # Used in: Renderer/Elements.js:26
    (r"\<(.*)>\((.*)\)", r"\1.<\2>")     # Used in Tween.js:24
]
# type converter
reTypeName =        re.compile(r"(Array\(|)\{(.+?)\}\)*(.*)$")

# Detect "Natural Docs" annotations.
reStarCom2Bloc =        re.compile(r"^ *\/\*\* *(?! )")
reLineCom2 =            re.compile(r"^ *\* *(?! )")
reEndComBloc =          re.compile(r"\*\/")
reEndLine =             re.compile(r"\n")
reProblematicEndLine =  re.compile(r"\\\n")

# Generic block start
reItemsBlockStart = re.compile(r".+\: *$")

# Items converters
reItemNamed =       re.compile(r"(\w+|\[\*\]) +- +(.+)$")
reItemUnnamed =     re.compile(r"(- |)(.+)$")
reItemSuperClass =  re.compile(r"- \<([\.\w]+)\> *$")

# Missing parameters
reMisingParameters = re.compile(r"^ *(\w+\.*)\ *(=|:) *function\(()\)(.*)$")

# Constants
# ---------
M_CODE = 0
M_COM2_BLOC = 1

def cnvJsDoc (inputFilename, outputFilename):
    print "Translating into jsDoc, input: %s output: %s " % (inputFilename, outputFilename),

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
    isBlankLine = True
    isCom2StartLine = False
    isCodeStartLine = True
    previousProblematicEndLine = False
    annotations = NaturalAnnotations(inputFilename)
    lineNumber = 0
    for line in fIn:
        lineNumber += 1
        startCom2 = -1
        endCom2 = -1
        if mode == M_CODE and not previousProblematicEndLine:
            oo = reStarCom2Bloc.search(line)
            if oo: 
                startCom2 = oo.end()
                mode = M_COM2_BLOC
                isCom2StartLine = True
                
        # Com2 line?
        if mode == M_COM2_BLOC:
            previousProblematicEndLine = False
            oo = reEndComBloc.search(line)
            if oo: 
                endCom2 = oo.start()
                mode = M_CODE
                isCodeStartLine = True
            if startCom2 == -1:
                oo = reLineCom2.search(line)
                if oo: 
                    startCom2 = oo.end()
            if endCom2 == -1:
                endCom2 = reEndLine.search(line).start()

            if startCom2 >= 0 and startCom2 < endCom2:
                line = ( line[:startCom2] + 
                         annotations.toJsDoc(
                            line[startCom2:endCom2], 
                            lineNumber, 
                            isBlankLine, 
                            isCom2StartLine) + 
                         line[endCom2:] )
                isBlankLine = False
                isCom2StartLine = False
            else:
                isBlankLine = True
        if mode == M_CODE: 
            if endCom2 == -1:
                if isCodeStartLine == True and len(annotations.headerBlockparams) > 0:
                    oo = reMisingParameters.search(line)
                    if oo:
                        line = re.sub(
                            reMisingParameters, 
                            r" \1 \2 function(" + 
                                ",".join(annotations.headerBlockparams) +
                                r")\4", 
                            line)
                isCodeStartLine = False
            if reProblematicEndLine.search(line):
                previousProblematicEndLine = True
            else:
                previousProblematicEndLine = False
        fOut.write(line)
                
    annotations.endsHeaderBlock() # Force to run checks
    if annotations.warnings == 0:
        print "   Done!"
    else:
        print "Done with %s warnings." % annotations.warnings
    fIn.close()
    fOut.close()
    return outputFilename
    
# -----------------
# Analyze comment blocks
# -----------------    
class NaturalAnnotations:
    def __init__(self, inputFilename):
        self.inputFilename = inputFilename
        logging.basicConfig(format='%(message)s', level=logging.DEBUG)
        self.warnings = 0
        self.clearHeaderBlock()
        self.clearBlock()

    def warning(self, text):
        if self.warnings == 0:
            print
        logging.warning(
            "%s:%s: WARNING - " % (self.inputFilename, self.srcLineNumber) +
            text +
            "\n    Keyword: \"%s\"\n" % self.srcSource)
        self.warnings += 1    
    def headerWarning(self, text):
        if self.warnings == 0:
            print
        logging.warning(
            "%s:%s: WARNING - " % (self.inputFilename, self.headerSrcLineNumber) +
            text +
            "\n    Keyword: \"%s\"\n" % self.headerSrcSource)
        self.warnings += 1
    
    def clearHeaderBlock(self):
        self.blocks = []
        self.ignores = []
        self.requires = []
        self.headerBlockparams = []
        self.headerBlockName = None

        # Process variables
        self.headerSrcLineNumber = 0
        self.headerSrcSource = ""
        self.processedBlocks = []

    def endsHeaderBlock(self):
        for r in self.requires:
            if not r in self.processedBlocks:
                self.headerWarning( 
                    "Required block \"%s\" missing in header block \"%s\"" % 
                    (r, self.headerBlockName)
                )
        self.endsBlock()
        self.clearHeaderBlock()
        
    def clearBlock(self):
        self.maxLines = sys.maxint
        self.minLines = 0
        self.prefixLine = ""
        self.lineConv = None
        
        # Process variables
        self.srcLineNumber = 0
        self.srcSource = ""
        self.processedLines = 0
        self.currentModeBlock = None
        self.blockName = None
        
    def endsBlock(self):
        if self.processedLines < self.minLines:
            self.warning("Required %s line(s)." % self.minLines)
        self.clearBlock()
    

    def toJsDoc(self, line, lineNumber, prevBlankLine, isStartLine):
        if isStartLine:
            self.endsHeaderBlock()

        # Is a new block
        for k, v in syntax.iteritems():
            for j in v["keywords"]:
                if re.match(j, line, flags=re.IGNORECASE):
                    self.endsBlock()
                    
                    # Load block converter
                    # ---------------
                    # Start block
                    self.srcLineNumber = lineNumber
                    self.srcSource = line
                    self.blockName = k
                    self.currentModeBlock = v
                    # Is header block
                    if isStartLine:
                        self.headerSrcLineNumber = lineNumber
                        self.headerSrcSource = line
                        self.headerBlockName = k
                        if v.get("blocks"):
                            self.blocks = v.get("blocks")
                        if v.get("ignores"):
                            self.ignores = v.get("ignores")
                        if v.get("requires"):
                            self.requires = v.get("requires")
                    # Is not header block
                    elif self.headerBlockName:
                        if not self.blockName in self.blocks : 
                            if not self.blockName in self.ignores:
                                self.warning(
                                    "\"%s\" not alowed in header block \"%s\"." % 
                                    (self.blockName, self.headerBlockName)
                                )
                            self.clearBlock() # Block is ignored
                            break

                    # Warnings
                    if "chks" in self.currentModeBlock:
                        chks = self.currentModeBlock.get("chks")
                        for chk in chks:
                            if chk == "prevBlank" and prevBlankLine == False:
                                self.warning("No previus blank line.")
                            if chk == "isStartLine" and isStartLine == False:
                                self.warning("Is not start line.")
                            if chk == "requiresHeader" and not  self.headerBlockName:
                                # Block not alowed without header block
                                self.warning( 
                                    "Block \"%s\" not alowed without header block." % 
                                    self.blockName
                                )
                                self.clearBlock() # Block is ignored
                                break
                        if not self.currentModeBlock:
                            # Block is ignored
                            break

                    # Load line converter
                    # -------------------
                    if v.get("lines"):
                        lines = v.get("lines")
                        if lines.get("prefixLine"):
                            self.prefixLine = lines.get("prefixLine")
                        if lines.get("lineConv"):
                            self.lineConv = lines.get("lineConv")
                        if lines.get("maxLines"):
                            self.maxLines = lines.get("maxLines")
                        if lines.get("minLines"):
                            self.minLines = lines.get("minLines")

                    # Convert the block
                    # -----------------
                    self.processedBlocks.append(self.blockName)
                    if "blockConv" in self.currentModeBlock:
                        conv = self.currentModeBlock["blockConv"]
                        if conv == "cnvKeywordJsDoc":
                            line = self.cnvKeywordJsDoc(line)
                    if "prefixBlockKeyword" in self.currentModeBlock:
                        line = self.currentModeBlock["prefixBlockKeyword"] + " " + line
                    break
            else:
                continue
            break
        # The block will continue
        else:
            # New block to not parse
            if reItemsBlockStart.search(line) and prevBlankLine:
                self.endsBlock() # forced end of previus block
            # Is a line into a block
            elif self.currentModeBlock and self.lineConv:
                conv = self.lineConv
                if conv == "itemNamed":
                    line = self.cnvItemNamed(line, False)
                elif conv == "itemOptionalNamed":
                    line = self.cnvItemNamed(line, True)
                elif conv == "itemUnnamed":
                    line = self.cnvItemUnnamed(line)
                elif conv == "itemSuperClass":
                    line = self.cnvItemSuperClass(line)

                if self.maxLines <= self.processedLines:
                    self.endsBlock()  # forced end of block
        return line

    # Keyword line converters
    def cnvKeywordJsDoc(self, subLine):
        words = subLine.split(None,1)
        if len(words) < 2:
            return subLine

        decl = self.cnvTypeDeclaration(words[1])
        if decl == None:
            return subLine

        return (words[0] + 
                " {" + decl["typeName"] + "} " + 
                decl["remainder"])

    # Line converters
    def cnvItemSuperClass(self, subLine):
        oo = reItemSuperClass.search(subLine)
        if oo == None:
            return subLine
        self.processedLines += 1
        return (self.prefixLine + " {" + oo.group(1) + "}")

    def cnvItemNamed(self, subLine, isOptional):
        oo = reItemNamed.search(subLine.replace("} or {","|"))
        if oo == None:
            return subLine
        decl = self.cnvTypeDeclaration(oo.group(2))
        if decl == None:
            return subLine
        
        paramName = oo.group(1)
        if paramName == "[*]":
            paramName = "dummyParam"
        self.processedLines += 1 # must be increased before parse the line, 
                                 # since parsing may end the block.
        if self.prefixLine == "@param":
            self.headerBlockparams.append(paramName)
        if isOptional:
            result = (self.prefixLine +
                " {" + decl["typeName"] + "|null|undefined=} " +
                paramName + " " + 
                decl["remainder"])
        else:
            if decl["typeName"] == "Object" and paramName == "options":
                result = (self.prefixLine +
                    " {Object=} options " + 
                    decl["remainder"])
                self.endsBlock() # forced end of block
            else:
                result = (self.prefixLine +
                        " {" + decl["typeName"] + "} " +
                        paramName + " " + 
                        decl["remainder"])
        return result

    def cnvItemUnnamed(self, subLine):
        if reItemUnnamed.search(subLine) == None:
            return subLine
        decl = self.cnvTypeDeclaration(subLine.replace("} or {","|"))
        if decl == None:
            return subLine

        self.processedLines += 1
        return (self.prefixLine + 
                " {" + decl["typeName"] + "} " + 
                decl["remainder"])

    # Type converter
    def cnvTypeDeclaration(self, subLine):
        oo = reTypeName.search(subLine)
        if oo:
            if oo.group(1):
                return {"typeName":  self.cnvTypeList("Array(" + oo.group(2) + ")"), 
                        "remainder": oo.group(3)}
            else:
                return {"typeName": self.cnvTypeList(oo.group(2)), 
                        "remainder": oo.group(3)}
        else:
            return None

    def cnvTypeList(self, typeList):
        repetitiveParameter = ""
        if typeList[-4:] == " ...":
            typeList = typeList[:-4]
            repetitiveParameter = "..."
        return repetitiveParameter + self.cnvTypeName(typeList)

    def cnvTypeName(self, typeName):
        if typeName == "":
            return "*" # Any type from declaration as {}

        for p, r in typesOL:
            if r.find(r"\2") > 0:
                spl = re.split(p,typeName)
                if len(spl) >= 4 and spl[1] != "" and spl[2] != "":
                    typeName = re.sub(p,r,typeName)
                    typeName = typeName.replace(spl[1], self.cnvTypeName(spl[1]))
                    typeName = typeName.replace(spl[2], self.cnvTypeName(spl[2]))
                    return self.cnvTypeNameSplit(typeName)
            elif r.find(r"\1") > 0:
                spl = re.split(p,typeName)
                if len(spl) >= 3 and spl[1] != "":
                    typeName = re.sub(p,r,typeName)
                    typeName = typeName.replace(spl[1], self.cnvTypeName(spl[1]))
                    return self.cnvTypeNameSplit(typeName)
            else:
                if typeName.lower() == p.lower():
                    return r

        return self.cnvTypeNameSplit(typeName)

    def cnvTypeNameSplit(self, typeName):
        typeName = typeName.replace(" or ","|")
        typeName = typeName.replace("||","|") # Used in Event.js
        typeName = typeName.replace(" ","")
        types = typeName.split("|")
        if len(types) > 1:
            for i in range(len(types)):
                types[i] = self.cnvTypeName(self.cnvTypeNameClear(types[i]))
            return "|".join(types)
        else:
            return self.cnvTypeNameClear(typeName)

    def cnvTypeNameClear(self, typeAux):
        if typeAux[0:1] == "{" and typeAux[len(typeAux)-1:] == "}": # See Protocol.js:105
            typeAux = typeAux[1:-1]
        if typeAux[0:1] == "<" and typeAux[len(typeAux)-1:] == ">":
            typeAux = typeAux[1:-1]
        return typeAux

# -----------------
# main
# -----------------
if __name__ == '__main__':
    cnvJsDoc(sys.argv[1], sys.argv[2])
