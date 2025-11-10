-- =====================================================================
-- PostgreSQL RPC Function for Bulk DELETE Operations
-- =====================================================================
-- This function allows efficient bulk deletion of records using POST
-- with request body instead of GET with URL parameters, avoiding
-- "URI too long" errors when deleting 1,000+ records.
-- =====================================================================

-- Create the bulk delete function in the wh40k schema
CREATE OR REPLACE FUNCTION wh40k.delete_by_ids(
    p_table_name text,
    p_column_name text,
    p_ids text[]
)
RETURNS int AS $$
DECLARE
    v_deleted_count int;
    v_query text;
BEGIN
    -- Validate that the table exists in the wh40k schema
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = 'wh40k'
          AND table_name = p_table_name
    ) THEN
        RAISE EXCEPTION 'Table wh40k.% does not exist', p_table_name;
    END IF;

    -- Build DELETE query safely using format() to prevent SQL injection
    -- %I = identifier (table/column names) - properly quoted
    -- $1 = parameter placeholder for the IDs array
    v_query := format(
        'DELETE FROM wh40k.%I WHERE %I = ANY($1)',
        p_table_name,
        p_column_name
    );

    -- Execute the DELETE query with the IDs array as a parameter
    EXECUTE v_query USING p_ids;

    -- Get the number of rows deleted
    GET DIAGNOSTICS v_deleted_count = ROW_COUNT;

    RETURN v_deleted_count;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant execute permission to Supabase roles
GRANT EXECUTE ON FUNCTION wh40k.delete_by_ids(text, text, text[]) TO anon, authenticated, service_role;

-- =====================================================================
-- Usage Examples
-- =====================================================================
--
-- Delete records from datasheets_abilities where datasheet_id is in the list:
-- SELECT wh40k.delete_by_ids('datasheets_abilities', 'datasheet_id', ARRAY['id1', 'id2', 'id3']);
--
-- Python usage via Supabase client:
-- result = supabase.rpc('delete_by_ids', {
--     'p_table_name': 'datasheets_abilities',
--     'p_column_name': 'datasheet_id',
--     'p_ids': list_of_ids  # Can be 1,671+ IDs without URI length issues!
-- }).execute()
--
-- Returns: Integer count of deleted rows
-- =====================================================================
