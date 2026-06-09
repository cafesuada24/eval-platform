# Metric Registry Sorting Design Spec

- **Date**: 2026-06-09
- **Status**: Approved
- **Author**: Antigravity

## 1. Background & Goals

Currently, the Metrics Registry page displays primitive and AI-judged evaluation metrics in the order they are received from the backend API. There is no mechanism to sort the list.

The goal is to implement sorting capabilities in the sidebar list component (`MetricsList.tsx`) of the Metrics Registry page, allowing users to order metrics alphabetically (A-Z / Z-A) or by their type (AI Judge first vs. Primitive first).

## 2. Architecture & UI Layout

We will wrap the existing search input and a new sorting icon button inside a flexbox container within [MetricsList.tsx](file:///home/serein/SourceCodes/eval-platform/frontend/components/metrics/MetricsList.tsx).

### 2.1 UI Component Changes
- **Trigger Button**: A small, icon-only button containing the `<ArrowUpDown />` icon from `lucide-react`, matching the heights and border styles of the search input.
- **Dropdown Menu**: When clicked, the button opens a `<DropdownMenu>` containing:
  - Name (A - Z) [Selected by default]
  - Name (Z - A)
  - Type (AI Judge First)
  - Type (Primitive First)
- **Selection Indicator**: An active sorting option will show a `<Check className="h-3 w-3" />` icon on the right side of the dropdown item.

## 3. Sorting Logic

We define a state variable `sortBy` and update the list filtration `useMemo` block to sort the filtered array before rendering:

```typescript
type SortOption = "name-asc" | "name-desc" | "type-ai" | "type-primitive"

const [sortBy, setSortBy] = useState<SortOption>("name-asc")
```

The sorting logic inside `useMemo` will copy the filtered array and sort it:
1. **Name (A-Z)**: `a.name.localeCompare(b.name)`
2. **Name (Z-A)**: `b.name.localeCompare(a.name)`
3. **Type (AI Judge First)**: AI-Judge metrics come first. If types are equal, tie-break by name alphabetically.
4. **Type (Primitive First)**: Primitive metrics come first. If types are equal, tie-break by name alphabetically.

## 4. Verification & Testing

To ensure correctness and prevent regressions:
- A new or updated unit test will verify the sort dropdown correctly sorts a mock array of metrics in all four directions.
- Perform visual testing of the sidebar header to ensure layout aligns correctly across responsive widths.

## 5. Trade-offs

- **Direct Sorting vs. Backend Sorting**: We perform sorting client-side. Since the list of metrics is small (typically <100) and already fetched in its entirety, client-side sorting is extremely fast and avoids extra round-trips to the server.
- **Icon Trigger vs. Text Trigger**: An icon button is used to save valuable horizontal space in the narrow left pane of the SplitLayout, avoiding wrapping search inputs.
