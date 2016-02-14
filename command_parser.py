#!/usr/bin/env python2.6
import logging
import re

logger = logging.getLogger('command_parser')


class Configparse(str):
    """
    Version 1.1
    3/4/2011
    Added searchall and searchpat methods to support new flags.
    """

    def __init__(self, output):
        str.__init__(output)

    def exist(self, pat):
##        print(self)
##        print(pat)
        if re.search(pat, self):
            return True
        else:
            return False
    
    def existl(self, list_pat):
        self._result = []
        for pat in list_pat:
            self._result.append(self.exist(pat))
        return self._result

    def notexist(self, pat):
        if self.exist(pat):
            return False
        else:
            return True
    
    def notexistl(self, list_pat):
        self._result = []
        for pat in list_pat:
            self._result.append(self.notexist(pat))
        return self._result

    def count(self, pat):
        return len(re.findall(pat, self))
    
    def countl(self, list_pat):
        self._result = []
        for pat in list_pat:
            self._result.append(self.count(pat))
        return self._result

    def countcmpl(self, list_pat, mult=1):
        self._count = len(re.findall(list_pat[0], self))
        self._result = []
        try:
            for pat in list_pat[1:]:
                if len(re.findall(pat, self)) * mult != self._count:
                    self._result.append(False)
                    return self._result
            if self._count == 0:
                self._result.append(None)
            else:
                self._result.append(True)
            return self._result
        except:
            return "Error:  Problem in the Pattern List"
        
    def searchpat(self, pat):
        return re.search(pat, self)
    
    def searchall(self, pat):
        return re.findall(pat, self)


def commandparse(output, pattern_dic):
    """
    Version 1.1
    3/4/2011
    Added countcmpnuml - count occurrences of a pattern and compare the number to a logical expression supplied
    in a tuple of form ('stswshm1.st', r'> 1').  The method should be given a list of tuples.  Returns true
    if the expression evaluates to true.
    
    Added countcmpnumzl - same as countcmpnuml except that True will also be returned if the pattern
    matches zero occurrences.
    
    Added numcmpl - extract a number from the output object and compare to a logical expression supplied in a
    tuple of form (r'\((\d+) bytes free\)', '> 16000000').  The method should be given a list of tuples.
    Returns true if the expression evaluates to true.
    """
    
    #print pattern_dic
    resultd = {}
    for flag in pattern_dic.keys():
        logger.debug("commandparse: flag: {}".format(flag))
        pat = pattern_dic[flag]
        logger.debug("commandparse: pattern: {}".format(pat))
        #print flag
        #print pat
        if flag == 'exist':
            result = output.exist(pat)
        elif flag == 'existl':
            result = output.existl(pat)
        elif flag == 'notexist':
            result = output.notexist(pat)
        elif flag == 'notexistl':
            result = output.notexistl(pat)
        elif flag == 'count':
            result = output.count(pat)
        elif flag == 'countl':
            result = output.countl(pat)
        elif flag == 'countcmpl':
            result = output.countcmpl(pat[0], mult=pat[1])
        elif flag == 'countcmpnuml':
            """
            count occurrences of a pattern and compare the number to a supplied number
            """
            result = []
            pats = [i for i, j in pat]
            nums = [j for i, j in pat]
            resultp = output.countl(pats)
            try:
                result = map((lambda r, op : eval(str(float(r)) + op)), resultp, nums)
            except:
                result = ["Error in List or Regular Expression"]
        elif flag == 'countcmpnumzl':
            result = []
            pats = [i for i, j in pat]
            nums = [j for i, j in pat]
            resultp = output.countl(pats)
            try:
                result = map((lambda r, op : eval(str(float(r)) + op) or r == 0), resultp, nums)
            except:
                result = ["Error in List or Regular Expression"]
        elif flag == 'numcmpl':
            """
            extract a number using the pat
            compare the number to a supplied number
            """""
            result = []
            pats = [i for i, k in pat]
            nums = [k for i, k in pat]
            resultp = map((lambda pat : output.searchall(pat)), pats)
            fail = 0
            m = 0
            for rl in resultp:
                op = nums[m]
                for r in rl:
                    if not eval(str(float(r)) + op):
                        fail = 1
                m += 1
                if fail:
                    result.append(False)
                else:
                    result.append(True)
        else:
            result = "Error:  "  + flag + " =Unsupported Flag"
        resultd[flag] = result
    return resultd        