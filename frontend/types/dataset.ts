import { z } from "zod";

export const FileAssetSchema = z.object({
  file_id: z.string(),
  filename: z.string(),
  url: z.string(),
});

export type FileAsset = z.infer<typeof FileAssetSchema>;

export const DynamicDictSchema = z.record(z.string(), z.any());

export const DatasetSchemaDefinition = z.object({
  inputs: z.record(z.string(), z.string()),
  outputs: z.record(z.string(), z.string()),
});

export const TestCaseSchema = z.object({
  id: z.string().optional(),
  inputs: DynamicDictSchema,
  expected_outputs: DynamicDictSchema,
  metadata: DynamicDictSchema.optional(),
});

export type TestCase = z.infer<typeof TestCaseSchema>;

export const DatasetSchema = z.object({
  id: z.string(),
  name: z.string(),
  schema: DatasetSchemaDefinition,
  created_at: z.string().optional(),
  updated_at: z.string().optional(),
});

export type Dataset = z.infer<typeof DatasetSchema>;

export const PaginatedTestCasesSchema = z.object({
  items: z.array(TestCaseSchema),
  total: z.number(),
  page: z.number(),
  limit: z.number(),
});

export type PaginatedTestCases = z.infer<typeof PaginatedTestCasesSchema>;
