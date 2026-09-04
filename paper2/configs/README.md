# Configurations

研究方向确定后，在主题子目录中保存数据、训练、评价和复现实验配置。

`blockstamp/minimal_probe.yaml` 使用 JSON-compatible YAML，冻结三个 diode-RC profile、
三个 smooth-NMOS ring 实例、producer precision/tolerance 和只依赖 residual/local
Jacobian 的 tube-radius rule。配置明确将 Decimal-160 标为 non-rigorous、post-hoc
high-precision test reference。
