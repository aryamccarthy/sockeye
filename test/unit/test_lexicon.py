# Copyright 2017 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not
# use this file except in compliance with the License. A copy of the License
# is located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is distributed on
# an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
# express or implied. See the License for the specific language governing
# permissions and limitations under the License.

import os
from tempfile import TemporaryDirectory

import numpy as np

import sockeye.constants as C
import sockeye.lexicon


def test_topk_lexicon():
    lexicon = ["a\ta\t-0.6931471805599453",
               "a\tb\t-1.2039728043259361",
               "a\tc\t-1.6094379124341003",
               "b\tb\t0.0"]
    vocab_list = ["a", "b", "c"]
    vocab = dict((y, x) for (x, y) in enumerate(C.VOCAB_SYMBOLS + vocab_list))
    k = 2
    lex = sockeye.lexicon.TopKLexicon(vocab, vocab)

    # Create from known lexicon
    with TemporaryDirectory(prefix="test_topk_lexicon.") as work_dir:
        # Write fast_align format lex table
        input_lex_path = os.path.join(work_dir, "input.lex")
        with open(input_lex_path, "w") as out:
            for line in lexicon:
                print(line, file=out)
        # Use fast_align lex table to build top-k lexicon
        lex.create(input_lex_path, k)

        # Test against known lexicon
        expected = np.zeros((len(C.VOCAB_SYMBOLS) + len(vocab_list), k), dtype=np.int)
        # a -> special + a b
        expected[len(C.VOCAB_SYMBOLS), :2] = [len(C.VOCAB_SYMBOLS), len(C.VOCAB_SYMBOLS) + 1]
        # b -> special + b
        expected[len(C.VOCAB_SYMBOLS) + 1, :1] = [len(C.VOCAB_SYMBOLS) + 1]
        assert np.all(lex.lex == expected)

        # Test save/load
        expected_sorted = np.sort(expected, axis=1)
        json_lex_path = os.path.join(work_dir, "lex.json")
        lex.save(json_lex_path)
        lex.load(json_lex_path)
        assert np.all(lex.lex == expected_sorted)

        def make_src_batch(words):
            # size (1, src_len)
            return np.array([[vocab[word] for word in words]], dtype=np.int)

        def make_trg(words):
            # size (trg_len)
            return np.array([vocab[word] for word in words], dtype=np.int)

        # Test lookup

        src_ids = make_src_batch(["a"])
        expected_size = lex.get_trg_ids_size(*src_ids.shape)
        gold_expected_size = len(C.VOCAB_SYMBOLS) + (k * 1)
        assert expected_size == gold_expected_size
        trg_ids = lex.get_trg_ids(src_ids)
        gold_trg_ids = make_trg(C.VOCAB_SYMBOLS + ["a", "b"])
        assert np.all(trg_ids == gold_trg_ids)

        src_ids = make_src_batch(["b"])
        expected_size = lex.get_trg_ids_size(*src_ids.shape)
        gold_expected_size = len(C.VOCAB_SYMBOLS) + (k * 1)
        assert expected_size == gold_expected_size
        trg_ids = lex.get_trg_ids(src_ids)
        gold_trg_ids = make_trg(C.VOCAB_SYMBOLS + ["b", C.PAD_SYMBOL])
        assert np.all(trg_ids == gold_trg_ids)

        src_ids = make_src_batch(["c"])
        expected_size = lex.get_trg_ids_size(*src_ids.shape)
        gold_expected_size = len(C.VOCAB_SYMBOLS) + (k * 1)
        assert expected_size == gold_expected_size
        trg_ids = lex.get_trg_ids(src_ids)
        gold_trg_ids = make_trg(C.VOCAB_SYMBOLS + [C.PAD_SYMBOL, C.PAD_SYMBOL])
        assert np.all(trg_ids == gold_trg_ids)

        src_ids = make_src_batch(["a", "b"])
        expected_size = lex.get_trg_ids_size(*src_ids.shape)
        # Capped to special + vocab_size
        gold_expected_size = len(C.VOCAB_SYMBOLS) + 3
        assert expected_size == gold_expected_size
        trg_ids = lex.get_trg_ids(src_ids)
        # Capped to special + vocab_size
        gold_trg_ids = make_trg(C.VOCAB_SYMBOLS + ["a", "b", C.PAD_SYMBOL])
        assert np.all(trg_ids == gold_trg_ids)

        src_ids = make_src_batch(["a", "b", "c"])
        expected_size = lex.get_trg_ids_size(*src_ids.shape)
        # Capped to special + vocab_size
        gold_expected_size = len(C.VOCAB_SYMBOLS) + 3
        assert expected_size == gold_expected_size
        trg_ids = lex.get_trg_ids(src_ids)
        # Capped to special + vocab_size
        gold_trg_ids = make_trg(C.VOCAB_SYMBOLS + ["a", "b", C.PAD_SYMBOL])
        assert np.all(trg_ids == gold_trg_ids)

        # Test smaller k
        small_k = k - 1
        lex.load(json_lex_path, k=small_k)
        assert lex.lex.shape[1] == small_k
        src_ids = make_src_batch(["a"])
        expected_size = lex.get_trg_ids_size(*src_ids.shape)
        gold_expected_size = len(C.VOCAB_SYMBOLS) + (small_k * 1)
        assert expected_size == gold_expected_size
        trg_ids = lex.get_trg_ids(src_ids)
        gold_trg_ids = make_trg(C.VOCAB_SYMBOLS + ["a"])
        assert np.all(trg_ids == gold_trg_ids)

        # Test larger k
        large_k = k + 1
        lex.load(json_lex_path, k=large_k)
        # Can only load k
        assert lex.lex.shape[1] == k
        src_ids = make_src_batch(["a", "c"])
        expected_size = lex.get_trg_ids_size(*src_ids.shape)
        # Capped to special + vocab_size
        gold_expected_size = len(C.VOCAB_SYMBOLS) + 3
        assert expected_size == gold_expected_size
        trg_ids = lex.get_trg_ids(src_ids)
        gold_trg_ids = make_trg(C.VOCAB_SYMBOLS + ["a", "b", C.PAD_SYMBOL])
        assert np.all(trg_ids == gold_trg_ids)
