# 15. Performance Optimization: Storage and Data Pipelines


GPUs waiting for data is the most common hidden bottleneck. Symptoms are low `SM_ACTIVE`, high CPU iowait, and sawtooth GPU utilization.

- **Local NVMe cache:** Stage datasets onto local NVMe (with an init container or a CSI cache driver).
- **Parallel file systems:** Lustre, GPFS, WEKA, VAST, or DDN for large-scale training, via their CSI drivers.
- **GPUDirect Storage (GDS):** A DMA path from NVMe/NFS-over-RDMA directly into GPU memory. Enable it with `--set gds.enabled=true` (deploys `nvidia-fs`). Apps use cuFile (for example via DALI or kvikio).
- **Data loader tuning:**
  - PyTorch: `num_workers` = roughly CPU cores ÷ GPUs, `pin_memory=True`, `persistent_workers=True`, `prefetch_factor=2..4`.
  - Do preprocessing (decode, augment) on the **GPU** with **NVIDIA DALI**.
  - Use sharded, sequential formats (WebDataset, TFRecord, MosaicML Streaming, Parquet) rather than millions of small files.
- **Checkpointing:** Use asynchronous or distributed checkpointing (PyTorch DCP, NeMo async checkpoints) so GPUs don't stall during saves.
