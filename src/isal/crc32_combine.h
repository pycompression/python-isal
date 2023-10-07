/* pigz.c -- parallel implementation of gzip
 * Copyright (C) 2007-2023 Mark Adler
 * Version 2.8  19 Aug 2023  Mark Adler
 */

/*
  This software is provided 'as-is', without any express or implied
  warranty. In no event will the author be held liable for any damages
  arising from the use of this software.

  Permission is granted to anyone to use this software for any purpose,
  including commercial applications, and to alter it and redistribute it
  freely, subject to the following restrictions:

  1. The origin of this software must not be misrepresented; you must not
     claim that you wrote the original software. If you use this software
     in a product, an acknowledgment in the product documentation would be
     appreciated but is not required.
  2. Altered source versions must be plainly marked as such, and must not be
     misrepresented as being the original software.
  3. This notice may not be removed or altered from any source distribution.

  Mark Adler
  madler@alumni.caltech.edu

 */

/* 
Alterations from original:
- typedef for crc_t
- local declarations replaced with static inline
- g.block selector in crc32_comb removed
*/

#include <stdint.h>
#include <stddef.h>

typedef uint32_t crc_t;

// CRC-32 polynomial, reflected.
#define POLY 0xedb88320

// Return a(x) multiplied by b(x) modulo p(x), where p(x) is the CRC
// polynomial, reflected. For speed, this requires that a not be zero.
static inline crc_t multmodp(crc_t a, crc_t b) {
    crc_t m = (crc_t)1 << 31;
    crc_t p = 0;
    for (;;) {
        if (a & m) {
            p ^= b;
            if ((a & (m - 1)) == 0)
                break;
        }
        m >>= 1;
        b = b & 1 ? (b >> 1) ^ POLY : b >> 1;
    }
    return p;
}

// Table of x^2^n modulo p(x).
static const crc_t x2n_table[] = {
    0x40000000, 0x20000000, 0x08000000, 0x00800000, 0x00008000,
    0xedb88320, 0xb1e6b092, 0xa06a2517, 0xed627dae, 0x88d14467,
    0xd7bbfe6a, 0xec447f11, 0x8e7ea170, 0x6427800e, 0x4d47bae0,
    0x09fe548f, 0x83852d0f, 0x30362f1a, 0x7b5a9cc3, 0x31fec169,
    0x9fec022a, 0x6c8dedc4, 0x15d6874d, 0x5fde7a4e, 0xbad90e37,
    0x2e4e5eef, 0x4eaba214, 0xa8a472c0, 0x429a969e, 0x148d302a,
    0xc40ba6d0, 0xc4e22c3c};

// Return x^(n*2^k) modulo p(x).
static inline crc_t x2nmodp(size_t n, unsigned k) {
    crc_t p = (crc_t)1 << 31;       // x^0 == 1
    while (n) {
        if (n & 1)
            p = multmodp(x2n_table[k & 31], p);
        n >>= 1;
        k++;
    }
    return p;
}

// This uses the pre-computed g.shift value most of the time. Only the last
// combination requires a new x2nmodp() calculation.
static inline unsigned long crc32_comb(unsigned long crc1, unsigned long crc2,
                                       size_t len2) {
    return multmodp(x2nmodp(len2, 3), crc1) ^ crc2;
}
