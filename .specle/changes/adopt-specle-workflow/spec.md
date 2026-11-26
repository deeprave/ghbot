# Adopt Specle workflow

## Problem

ghbot has a local copy of portable agent workflow assets that should be replaced by the supported Specle workflow without losing ghbot-specific guidance or its specification history.

## Goal

Install the supported Specle workflow, preserve project-owned `.agents` state and guidance, and leave product behaviour unchanged.

## Boundaries

- This is a workflow-only migration: no product-code or report-contract changes.
- Preserve existing project guidance, specifications, active-state records, and tracker conventions.
- Its priority and start time remain a maintainer decision.

## Verification

Confirm the delivery prerequisite, validate the installed workflow inventory and root instructions, verify that project state is retained, and run workflow-specific checks only.
