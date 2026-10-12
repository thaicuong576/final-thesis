/**
 * Dynamic wording utilities for Source Lineage Drawer (LIN-1 / MKT-1 follow-up).
 *
 * Builds wording strictly from leaf reading, section, row_label, and real audit verdict.
 * Displays nothing if data is absent, eliminating generic placeholder claims.
 */

import type { LineageNode } from "./types";

/**
 * Format reading method into standard Vietnamese presentation.
 * Values: single | confirmed | confirmed_ocr_twice | visual | comparative_only
 */
export function formatReadingMethod(reading?: string | null): string | null {
  if (!reading) return null;
  const normalized = reading.trim().toLowerCase();
  switch (normalized) {
    case "single":
      return "Đối soát đơn (single)";
    case "confirmed":
      return "Đối soát xác nhận (confirmed)";
    case "confirmed_ocr_twice":
      return "Đối soát kép qua OCR (confirmed_ocr_twice)";
    case "visual":
      return "Đối soát trực quan (visual)";
    case "comparative_only":
      return "Kỳ so sánh (comparative_only)";
    default:
      return reading;
  }
}

/**
 * Extract leaf observation metadata recursively (reading, row_label, section, page).
 */
export function findLeafSourceMetadata(node: LineageNode): {
  rowLabel: string | null;
  reading: string | null;
  section: string | null;
  page: number | null;
} {
  if (!node.children || node.children.length === 0) {
    return {
      rowLabel: node.row_label || null,
      reading: node.reading || null,
      section: node.section || null,
      page: node.page ?? null,
    };
  }
  for (const child of node.children) {
    const leaf = findLeafSourceMetadata(child);
    if (leaf.reading || leaf.rowLabel || leaf.section) {
      return leaf;
    }
  }
  return {
    rowLabel: node.row_label || null,
    reading: node.reading || null,
    section: node.section || null,
    page: node.page ?? null,
  };
}

/**
 * Build dynamic detail text for the inputs step in JourneyTab.
 * Returns empty string if no metadata exists (never generic claims).
 */
export function buildInputStepDetail(
  rowLabel?: string | null,
  reading?: string | null
): string {
  const method = formatReadingMethod(reading);
  if (rowLabel && method) {
    return `Trích xuất từ chỉ tiêu '${rowLabel}' (phương thức: ${method}).`;
  }
  if (rowLabel) {
    return `Trích xuất từ chỉ tiêu '${rowLabel}'.`;
  }
  if (method) {
    return `Phương thức trích xuất: ${method}.`;
  }
  return "";
}

/**
 * Build dynamic audit verdict presentation for JourneyTab.
 * Returns null if no audit verdict is present (never claims 100% when no verdict).
 */
export function buildAuditVerdictPresentation(verdict?: {
  status?: string | null;
  reason?: string | null;
} | null): {
  title: string;
  detail: string;
  badge: string;
  badgeType: "success" | "warning";
} | null {
  if (!verdict || !verdict.status) {
    return null;
  }
  const isDropped = verdict.status === "dropped";
  const title = isDropped ? "Cảnh báo kiểm định: Đã loại bỏ" : "Kết quả thẩm định đối soát";
  const detail =
    verdict.reason ||
    (isDropped
      ? "Câu văn bị loại bỏ do không đạt yêu cầu kiểm định."
      : "Đã qua thẩm định kiểm định.");
  return {
    title,
    detail,
    badge: isDropped ? "Dropped" : "Verified",
    badgeType: isDropped ? "warning" : "success",
  };
}
