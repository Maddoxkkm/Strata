// Does RDNA3 (gfx1100) have usable matrix cores for what the prompt path needs, and how fast?
//
// The engine's prompt-attention and block-scorer kernels use hand-written gfx12 WMMA
// (`__builtin_amdgcn_wmma_f32_16x16x16_f16_w32_gfx12`, gated `#if defined(__gfx1200__) || defined(__gfx1201__)`),
// and upstream's own comment in src/kernels/cuda/qsa_select.cu:421 says "gfx1100 has WMMA too, with another
// layout". This probe answers the two questions a port depends on, without touching the engine:
//
//   1. correctness - one 16x16x16 f16 MMA through rocWMMA (the documented, layout-aware API that ships in this
//      ROCm) against an FP32 CPU reference;
//   2. throughput  - MMAs/s for the same instruction, i.e. the ceiling a gfx11 port could buy.
//
//   build: tools/hip/rebuild-windows.bat wmma_probe     (the ROCm + MSVC environment build_windows.bat sets up)
//   run:   build-hip-win\wmma_probe.exe
#include <hip/hip_runtime.h>
#include <rocwmma/rocwmma.hpp>

#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <vector>

using namespace rocwmma;

constexpr int N = 16;             // 16x16x16: the shape both engine kernels use

__global__ void mma_once(const _Float16* a, const _Float16* b, float* d) {
    fragment<matrix_a, N, N, N, _Float16, row_major> fa;
    fragment<matrix_b, N, N, N, _Float16, row_major> fb;
    fragment<accumulator, N, N, N, float> fc;
    load_matrix_sync(fa, a, N);
    load_matrix_sync(fb, b, N);
    fill_fragment(fc, 0.0f);
    mma_sync(fc, fa, fb, fc);
    store_matrix_sync(d, fc, N, mem_row_major);
}

__global__ void mma_many(const _Float16* a, const _Float16* b, float* d, int iters) {
    fragment<matrix_a, N, N, N, _Float16, row_major> fa;
    fragment<matrix_b, N, N, N, _Float16, row_major> fb;
    fragment<accumulator, N, N, N, float> fc;
    load_matrix_sync(fa, a, N);
    load_matrix_sync(fb, b, N);
    fill_fragment(fc, 1.0f);
    for (int i = 0; i < iters; ++i) mma_sync(fc, fa, fb, fc);
    store_matrix_sync(d, fc, N, mem_row_major);
}

static void check(hipError_t e, const char* what) {
    if (e != hipSuccess) {
        std::fprintf(stderr, "error: %s: %s\n", what, hipGetErrorString(e));
        std::exit(1);
    }
}

int main() {
    hipDeviceProp_t prop{};
    check(hipGetDeviceProperties(&prop, 0), "device properties");
    std::printf("device: %s (%s), hip %d.%d\n", prop.name, prop.gcnArchName, HIP_VERSION_MAJOR, HIP_VERSION_MINOR);

    std::vector<_Float16> a(N * N), b(N * N);
    std::vector<float> ref(N * N, 0.0f), got(N * N, 0.0f);
    for (int i = 0; i < N * N; ++i) {
        a[i] = (_Float16) (((i * 7) % 13) - 6) / 4.0f;
        b[i] = (_Float16) (((i * 5) % 11) - 5) / 4.0f;
    }
    for (int r = 0; r < N; ++r)
        for (int c = 0; c < N; ++c) {
            float s = 0;
            for (int k = 0; k < N; ++k) s += (float) a[r * N + k] * (float) b[k * N + c];
            ref[r * N + c] = s;
        }

    _Float16 *da, *db;
    float* dd;
    check(hipMalloc(&da, sizeof(_Float16) * N * N), "hipMalloc a");
    check(hipMalloc(&db, sizeof(_Float16) * N * N), "hipMalloc b");
    check(hipMalloc(&dd, sizeof(float) * N * N), "hipMalloc d");
    check(hipMemcpy(da, a.data(), sizeof(_Float16) * N * N, hipMemcpyHostToDevice), "copy a");
    check(hipMemcpy(db, b.data(), sizeof(_Float16) * N * N, hipMemcpyHostToDevice), "copy b");

    mma_once<<<1, 32>>>(da, db, dd);
    check(hipGetLastError(), "mma_once launch");
    check(hipDeviceSynchronize(), "mma_once sync");
    check(hipMemcpy(got.data(), dd, sizeof(float) * N * N, hipMemcpyDeviceToHost), "copy d");

    double worst = 0;
    for (int i = 0; i < N * N; ++i) worst = std::max(worst, std::fabs((double) got[i] - (double) ref[i]));
    std::printf("correctness: 16x16x16 f16 WMMA vs FP32 reference, max abs diff %.6f -> %s\n",
                worst, worst < 1e-3 ? "OK" : "MISMATCH");

    const int iters = 200000;
    const int launches = 5;
    mma_many<<<1, 32>>>(da, db, dd, 100);              // warm
    check(hipDeviceSynchronize(), "warm sync");
    hipEvent_t t0, t1;
    check(hipEventCreate(&t0), "event");
    check(hipEventCreate(&t1), "event");
    check(hipEventRecord(t0), "record");
    for (int i = 0; i < launches; ++i) mma_many<<<1, 32>>>(da, db, dd, iters);
    check(hipEventRecord(t1), "record");
    check(hipDeviceSynchronize(), "sync");
    float ms = 0;
    check(hipEventElapsedTime(&ms, t0, t1), "elapsed");
    const double mmas = (double) iters * launches;
    const double flops = mmas * 2.0 * N * N * N;       // 2*M*N*K per MMA
    std::printf("throughput: %.0f MMAs/s in one wave32 (%.1f TFLOP/s f16->f32, %.3f us per MMA)\n",
                mmas / (ms / 1000.0), flops / (ms / 1000.0) / 1e12, (ms * 1000.0) / mmas);
    return 0;
}
