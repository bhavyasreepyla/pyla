#!/usr/bin/env python3
"""tinylm: a character-level neural language model from scratch.

No ML frameworks -- just numpy and hand-derived backpropagation. The
architecture is the classic Bengio et al. (2003) neural probabilistic
language model:

    context of N chars -> embedding lookup -> tanh hidden layer -> softmax

Trained on the Pyla example programs in ./examples, so after training it
generates text that looks like Pyla source code. Every gradient below is
derived and written by hand; run with --check to verify them numerically
against finite differences.

Usage:
    python tinylm.py train              # train and save tinylm_model.npz
    python tinylm.py sample             # generate text from the saved model
    python tinylm.py sample --temp 0.5  # colder = more conservative
    python tinylm.py check              # numerical gradient check
"""

import argparse
import glob
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(HERE, "tinylm_model.npz")

BLOCK = 8        # context window: predict char N+1 from the previous 8
EMB = 16         # embedding dimension per character
HIDDEN = 128     # hidden layer width


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

def load_corpus():
    paths = sorted(glob.glob(os.path.join(HERE, "examples", "*.pyla")))
    if not paths:
        sys.exit("no .pyla files found in ./examples -- nothing to train on")
    parts = []
    for p in paths:
        with open(p, "r", encoding="utf-8") as f:
            parts.append(f.read())
    return "\n".join(parts)


def build_vocab(text):
    chars = sorted(set(text))
    stoi = {c: i for i, c in enumerate(chars)}
    itos = {i: c for i, c in enumerate(chars)}
    return stoi, itos


def build_dataset(text, stoi):
    """Sliding window: X[i] is BLOCK char-ids, Y[i] is the char that follows."""
    ids = np.array([stoi[c] for c in text], dtype=np.int64)
    n = len(ids) - BLOCK
    X = np.stack([ids[i:i + BLOCK] for i in range(n)])
    Y = ids[BLOCK:]
    return X, Y


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

def init_params(vocab_size, rng):
    return {
        "C":  rng.normal(0, 1.0, (vocab_size, EMB)),
        "W1": rng.normal(0, 1.0, (BLOCK * EMB, HIDDEN)) * (5 / 3) / (BLOCK * EMB) ** 0.5,
        "b1": np.zeros(HIDDEN),
        "W2": rng.normal(0, 1.0, (HIDDEN, vocab_size)) * 0.01,
        "b2": np.zeros(vocab_size),
    }


def forward(params, X):
    """Returns (loss-ready pieces). X: (B, BLOCK) int ids."""
    emb = params["C"][X]                          # (B, BLOCK, EMB)
    embcat = emb.reshape(X.shape[0], -1)          # (B, BLOCK*EMB)
    h = np.tanh(embcat @ params["W1"] + params["b1"])  # (B, HIDDEN)
    logits = h @ params["W2"] + params["b2"]      # (B, V)
    return embcat, h, logits


def softmax_loss(logits, Y):
    logits = logits - logits.max(axis=1, keepdims=True)  # stability
    exp = np.exp(logits)
    probs = exp / exp.sum(axis=1, keepdims=True)
    loss = -np.log(probs[np.arange(len(Y)), Y] + 1e-12).mean()
    return loss, probs


def backward(params, X, Y, embcat, h, probs):
    """Hand-derived gradients for cross-entropy -> softmax -> MLP -> embedding."""
    B = X.shape[0]

    # d(loss)/d(logits): softmax + cross-entropy collapses to (p - onehot)/B
    dlogits = probs.copy()
    dlogits[np.arange(B), Y] -= 1.0
    dlogits /= B

    grads = {}
    grads["W2"] = h.T @ dlogits                       # (HIDDEN, V)
    grads["b2"] = dlogits.sum(axis=0)                 # (V,)

    dh = dlogits @ params["W2"].T                     # (B, HIDDEN)
    dpre = dh * (1.0 - h * h)                         # tanh'(z) = 1 - tanh^2

    grads["W1"] = embcat.T @ dpre                     # (BLOCK*EMB, HIDDEN)
    grads["b1"] = dpre.sum(axis=0)                    # (HIDDEN,)

    dembcat = dpre @ params["W1"].T                   # (B, BLOCK*EMB)
    demb = dembcat.reshape(B, BLOCK, EMB)

    dC = np.zeros_like(params["C"])
    np.add.at(dC, X, demb)  # scatter-add: rows used many times accumulate
    grads["C"] = dC
    return grads


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------

def train(steps=20000, batch=64, seed=42):
    text = load_corpus()
    stoi, itos = build_vocab(text)
    V = len(stoi)
    X, Y = build_dataset(text, stoi)
    rng = np.random.default_rng(seed)
    params = init_params(V, rng)

    n_params = sum(p.size for p in params.values())
    print(f"corpus: {len(text):,} chars | vocab: {V} | "
          f"examples: {len(X):,} | parameters: {n_params:,}")

    for step in range(1, steps + 1):
        idx = rng.integers(0, len(X), batch)
        xb, yb = X[idx], Y[idx]
        embcat, h, logits = forward(params, xb)
        loss, probs = softmax_loss(logits, yb)
        grads = backward(params, xb, yb, embcat, h, probs)

        lr = 0.1 if step < steps * 0.75 else 0.01
        for k in params:
            params[k] -= lr * grads[k]

        if step == 1 or step % 2000 == 0:
            print(f"step {step:>6}  loss {loss:.4f}")

    # Full-dataset loss for an honest final number.
    _, _, logits = forward(params, X)
    final_loss, _ = softmax_loss(logits, Y)
    print(f"final loss over full dataset: {final_loss:.4f} "
          f"(untrained baseline would be ln({V}) = {np.log(V):.4f})")

    np.savez(MODEL_PATH, vocab="".join(sorted(stoi)), **params)
    print(f"saved model to {os.path.basename(MODEL_PATH)}")
    return params, stoi, itos


# ---------------------------------------------------------------------------
# Sampling
# ---------------------------------------------------------------------------

def load_model():
    if not os.path.exists(MODEL_PATH):
        sys.exit("no saved model -- run: python tinylm.py train")
    data = np.load(MODEL_PATH)
    vocab = str(data["vocab"])
    stoi = {c: i for i, c in enumerate(vocab)}
    itos = {i: c for i, c in enumerate(vocab)}
    params = {k: data[k] for k in ("C", "W1", "b1", "W2", "b2")}
    return params, stoi, itos


def sample(params, stoi, itos, prompt="let ", n=600, temperature=0.8, seed=None):
    rng = np.random.default_rng(seed)
    # Seed the context with the prompt (left-padded with newlines).
    pad = "\n" * BLOCK
    context = [stoi.get(c, 0) for c in (pad + prompt)[-BLOCK:]]
    out = list(prompt)
    for _ in range(n):
        xb = np.array([context])
        _, _, logits = forward(params, xb)
        logits = logits[0] / max(temperature, 1e-6)
        logits -= logits.max()
        probs = np.exp(logits)
        probs /= probs.sum()
        ci = rng.choice(len(probs), p=probs)
        out.append(itos[ci])
        context = context[1:] + [ci]
    return "".join(out)


# ---------------------------------------------------------------------------
# Numerical gradient check
# ---------------------------------------------------------------------------

def grad_check():
    """Verify the hand-written backward pass against finite differences."""
    rng = np.random.default_rng(0)
    V = 12
    params = init_params(V, rng)
    X = rng.integers(0, V, (5, BLOCK))
    Y = rng.integers(0, V, 5)

    embcat, h, logits = forward(params, X)
    _, probs = softmax_loss(logits, Y)
    grads = backward(params, X, Y, embcat, h, probs)

    eps = 1e-5
    print(f"{'param':<4} {'max rel error':>14}")
    ok = True
    for name in params:
        p = params[name]
        num = np.zeros_like(p)
        it = np.nditer(p, flags=["multi_index"])
        while not it.finished:
            ix = it.multi_index
            old = p[ix]
            p[ix] = old + eps
            lp, _ = softmax_loss(forward(params, X)[2], Y)
            p[ix] = old - eps
            lm, _ = softmax_loss(forward(params, X)[2], Y)
            p[ix] = old
            num[ix] = (lp - lm) / (2 * eps)
            it.iternext()
        denom = np.maximum(np.abs(num) + np.abs(grads[name]), 1e-8)
        rel = (np.abs(num - grads[name]) / denom).max()
        print(f"{name:<4} {rel:>14.2e}")
        ok = ok and rel < 1e-4
    print("gradient check:", "PASSED" if ok else "FAILED")
    return ok


# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("command", choices=["train", "sample", "check"])
    ap.add_argument("--steps", type=int, default=20000)
    ap.add_argument("--temp", type=float, default=0.8)
    ap.add_argument("-n", type=int, default=600)
    ap.add_argument("--prompt", default="let ")
    ap.add_argument("--seed", type=int, default=None)
    args = ap.parse_args()

    if args.command == "check":
        sys.exit(0 if grad_check() else 1)
    if args.command == "train":
        params, stoi, itos = train(steps=args.steps)
        print("\n--- sample from the freshly trained model ---")
        print(sample(params, stoi, itos, prompt=args.prompt,
                     n=args.n, temperature=args.temp, seed=args.seed))
        return
    params, stoi, itos = load_model()
    print(sample(params, stoi, itos, prompt=args.prompt,
                 n=args.n, temperature=args.temp, seed=args.seed))


if __name__ == "__main__":
    main()
