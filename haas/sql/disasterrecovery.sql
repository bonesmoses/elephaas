CREATE OR REPLACE VIEW v_dr_pairs AS
SELECT DISTINCT ON (herd_id)
       r.herd_id, r.instance_id, r.master_id, r.server_id,
       round(abs(coalesce(p.xlog_pos, 0) - coalesce(r.xlog_pos, 0)) / 1024.0, 1) AS mb_lag,
       h.vhost
  FROM ele_instance r
  JOIN ele_instance p ON (p.instance_id = r.master_id)
  JOIN ele_herd h ON (h.herd_id = r.herd_id)
 WHERE r.is_online
   AND r.master_id IS NOT NULL
 ORDER BY herd_id, mb_lag DESC, r.instance_id;
