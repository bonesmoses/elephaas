CREATE TRIGGER t_herd_audit_stamp_b_iu
       BEFORE INSERT OR UPDATE
    ON ele_herd
   FOR EACH ROW
       EXECUTE PROCEDURE sp_audit_stamps();
