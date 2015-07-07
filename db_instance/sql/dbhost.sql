CREATE TRIGGER t_host_audit_stamp_b_iu
       BEFORE INSERT OR UPDATE
    ON pgdb_host
   FOR EACH ROW
       EXECUTE PROCEDURE public.spc_update_audit_stamps();
