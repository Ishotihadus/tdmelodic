# -----------------------------------------------------------------------------
# Copyright (c) 2019-, PKSHA Technology Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.
# -----------------------------------------------------------------------------

import os
import subprocess
import sys

import Levenshtein
import MeCab


class Singleton:
    """Singleton pattern"""

    _instance = None

    def __new__(cls, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.is_initialized = False
        return cls._instance

    def __init__(self):
        self._instance.__init__(**kwargs)

    @property
    def singleton_initialized(cls):
        return cls.is_initialized

    @singleton_initialized.setter
    def singleton_initialized(self, boolean):
        assert boolean == True
        self.is_initialized = boolean


def get_mecab_default_path():
    out = subprocess.Popen(
        ["mecab-config", "--dicdir"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )
    stdout_, stderr_ = out.communicate()
    mecab_default_dir = stdout_.decode("utf-8").strip()
    return mecab_default_dir


mapping = [
    "surface",
    "pron",
    "kana",
    "pos",
    "goshu",
    "acc",
    "concat",
    "cost_uni",
    "cost_bi",
] + list(range(100))


class UniDic(Singleton):
    def __init__(
        self,
        unidic_path=None,
        mecabrc_path=os.path.dirname(os.path.abspath(__file__)) + "/my_mecabrc",
        verbose=False,
    ):
        if self.singleton_initialized:
            return
        else:
            self.singleton_initialized = True

            if unidic_path is None:
                self.unidic_path = get_mecab_default_path() + "/unidic"
            else:
                self.unidic_path = unidic_path
            self.mecabrc_path = mecabrc_path
            if verbose:
                print(
                    "ℹ️  [ MeCab setting ] unidic='{}'".format(self.unidic_path),
                    file=sys.stderr,
                )
                print(
                    "ℹ️  [ MeCab setting ] mecabrc='{}'".format(self.mecabrc_path),
                    file=sys.stderr,
                )

            self.__init_mecab()

    def __init_mecab(self):
        self.unidic_acc = MeCab.Tagger(
            "-d {dic} -r {rc} -Oacc".format(dic=self.unidic_path, rc=self.mecabrc_path)
        )

    def __parse(self, text, nbest=1, sep1="\t", sep2="\n"):
        parsed = self.unidic_acc.parseNBest(nbest, text)
        nbest = parsed.split("EOS\n")[:-1]  # remove the last entry
        ret = [
            [
                {mapping[i]: c for i, c in enumerate(list(l.split(sep1)))}
                for l in c.split(sep2)[:-1]
            ]
            for c in nbest
        ]
        return ret

    def get_n_best(self, text, kana_ref, nbest=20):
        """
        during inference, only the top 1 result is used. see data_loader.py
        """
        p = self.__parse(text, nbest=nbest)
        kanas = ["".join([e["pron"] for e in p_]) for p_ in p]
        dist = [Levenshtein.distance(k, kana_ref) for k in kanas]

        rank = [i for i, v in sorted(enumerate(dist), key=lambda v: v[1])]

        # rank = rank[0:3] if len(rank) >= 3 else rank # 上位 3 件を返す。
        # rank = rank[0:5] if len(rank) >= 5 else rank # 上位 5 件を返す。
        rank = rank[0:10] if len(rank) >= 10 else rank  # 上位 10 件を返す。

        ld = dist[rank[0]]
        return p, rank, ld

    def get_yomi(self, surface):
        words = self.unidic_acc.parse(surface)
        parsed = [word.split("\t") for word in words.split("\n")]
        yomis = [entry[1] for entry in parsed if len(entry) > 1]
        return "".join(yomis)
