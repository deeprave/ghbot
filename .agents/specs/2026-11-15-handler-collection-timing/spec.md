# Handler collection timing

## Defect

`_run_mode()` currently waits for `_main()` to return its complete pool result list before adding
anything to a mode collection. Mode units consequently expose only a processor type and do not
construct processors or receive completed results during the shared scan.

## Expected behaviour

The resolved mode constructs each processor and its collection receives a returned result inside
the TaskPool task, before scan completion. TaskPool retry and error handling remain unchanged.

## Root cause

The first refactor retained `_main(cfg, processor_cls)` and added a post-scan aggregation loop.

## Fix

Add a mode-aware scan path that invokes `mode.new_processor(...)`, submits a collection wrapper
to the pool, and adds only successfully returned results. Retain `_main()` for `info`.
